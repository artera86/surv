"""Discover native form fields and validate structured model answers."""
import json
import time

SCAN = r"""() => {
 const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
 const label = e => (e.labels?.length ? Array.from(e.labels).map(x=>x.innerText).join(' ') : e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.name || '').trim();
 const fields = Array.from(document.querySelectorAll('input,textarea,select')).filter(e => visible(e) && !e.disabled && !e.readOnly && !['hidden','submit','button','reset','image','file','password'].includes(e.type));
 const controls = fields.map((e,i) => {
   e.setAttribute('data-surv-field', String(i));
   const group = e.closest('fieldset,[role=group],[role=radiogroup]');
   return {id:String(i), type:e.tagName === 'SELECT' ? 'select' : e.type, name:e.name,
     label:label(e), question:group?.innerText?.slice(0,3000) || '', required:e.required,
     multiple:!!e.multiple, options:e.options ? Array.from(e.options).map(o=>({value:o.value,label:o.text,disabled:o.disabled})) : undefined};
 });
 const candidates = Array.from(document.querySelectorAll('button,input[type=submit],input[type=button],a,[role=button]')).filter(e=>visible(e)&&!e.disabled);
 const next = candidates.filter(e => /^(next|continue|submit|finish|done|proceed)(\s*[→›»])?$/i.test((e.innerText || e.value || e.getAttribute('aria-label') || '').trim()));
 next.forEach((e,i)=>e.setAttribute('data-surv-next',String(i)));
 return {text:document.body.innerText.slice(0,20000), controls, next:next.map((e,i)=>({id:String(i),label:e.innerText || e.value || e.getAttribute('aria-label')}))};
}"""


def discover(page):
    return page.evaluate(SCAN)


def fingerprint(page, data):
    return page.url, json.dumps(data, sort_keys=True)


def validate(answer, data):
    """Validate the whole plan before mutating any field."""
    plan = json.loads(answer)
    if not isinstance(plan, dict) or set(plan) != {'answers', 'next'}:
        raise ValueError('Expected JSON with answers and next')
    if not isinstance(plan['answers'], list) or not plan['answers']:
        raise ValueError('No answers supplied')
    fields = {c['id']: c for c in data['controls']}
    seen = set()
    radios = set()
    for item in plan['answers']:
        if not isinstance(item, dict) or set(item) != {'id', 'value'}:
            raise ValueError('Each answer needs id and value')
        key, value = item['id'], item['value']
        if not isinstance(key, str) or key not in fields or key in seen:
            raise ValueError('Unknown or duplicate control')
        seen.add(key)
        control = fields[key]
        kind = control['type']
        if kind in ('radio', 'checkbox'):
            if type(value) is not bool:
                raise ValueError('Selection must be boolean')
            if kind == 'radio' and value:
                group = control.get('name') or key
                if group in radios:
                    raise ValueError('Multiple answers in one radio group')
                radios.add(group)
        elif kind == 'select':
            values = value if control.get('multiple') else [value]
            allowed = {o['value'] for o in control['options'] if not o.get('disabled')}
            if not isinstance(values, list) or any(not isinstance(v, str) or v not in allowed for v in values):
                raise ValueError('Invalid select option')
        elif not isinstance(value, str):
            raise ValueError('Text answer must be a string')
    if plan['next'] not in {n['id'] for n in data['next']}:
        raise ValueError('Unknown Next button')
    return plan


def apply(page, data, plan):
    controls = {c['id']: c for c in data['controls']}
    for item in plan['answers']:
        field = page.locator('[data-surv-field="' + item['id'] + '"]')
        kind = controls[item['id']]['type']
        if kind in ('radio', 'checkbox'):
            field.set_checked(item['value'])
        elif kind == 'select':
            field.select_option(item['value'])
        else:
            field.fill(item['value'])
    page.locator('[data-surv-next="' + plan['next'] + '"]').click()


def run_auto(page, config, args, ask, is_done):
    instructions = (config['instructions'] + '\nReturn only a JSON object with keys answers and next. '
        'answers is a list of {"id":"control id","value":...}; next is a button id. '
        'Use booleans for radio/checkbox, option values for selects (list for multiple), strings for other inputs. '
        'Read the question text and labels. Include all relevant fields. Never invent personal facts. '
        'If facts are missing or the page cannot be answered, return {"answers":[],"next":null}.')
    seen = set()
    for index in range(config['max_pages']):
        if is_done(page, config):
            print('Completed.')
            return
        data = discover(page)
        state = fingerprint(page, data)
        if state in seen:
            raise RuntimeError('Repeated page; stopping')
        if not data['controls'] or not data['next']:
            raise RuntimeError('No supported form or Next button detected; configure selectors or a site adapter')
        seen.add(state)
        print(f'Page {index + 1}: generating…')
        answer = ask(data, instructions, args.model)
        plan = validate(answer, data)
        if fingerprint(page, discover(page)) != state:
            raise RuntimeError('Page changed during generation; stopping')
        print(json.dumps(plan, ensure_ascii=False))
        if args.preview:
            print('Preview complete; no fields changed.')
            return
        apply(page, data, plan)
        deadline = time.monotonic() + config['timeout_ms'] / 1000
        stable = None
        stable_since = time.monotonic()
        while time.monotonic() < deadline:
            if is_done(page, config):
                print('Completed.')
                return
            try:
                current = discover(page)
                marker = fingerprint(page, current)
                if marker != stable:
                    stable, stable_since = marker, time.monotonic()
                if marker != state and current['controls'] and current['next'] and time.monotonic() - stable_since >= 0.6:
                    break
            except Exception as exc:
                from playwright.sync_api import Error
                if not isinstance(exc, Error):
                    raise
            page.wait_for_timeout(200)
        else:
            raise TimeoutError('Next form not detected; check validation or configure a done selector')
    print('Reached max_pages; stopped.')

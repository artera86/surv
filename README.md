# Playwright + Codex

A Python command-line app: open a starting URL, read the questions and form controls, ask Codex for answers, enter them, click Next, and repeat. Automatic discovery and manually configured selectors are available.

## Automatic form mode

After setup, run:

```sh
python runner.py 'https://example.com/start' --config config.auto.json --preview
python runner.py 'https://example.com/start' --config config.auto.json --login
```

Edit `config.auto.json` with your answer instructions and any facts needed to answer. Automatic mode discovers visible native inputs, textareas, radio buttons, checkboxes, and selects in the main frame. It sends page text, field labels, fieldset context, and available choices to Codex. A structured answer plan is validated before fields are changed. Recognized navigation labels include Next, Continue, Submit, Finish, Done, and Proceed. `--auto` also enables discovery with an existing configuration.

Use `--preview` to inspect the proposed answers without filling or clicking. Normal mode clicks the chosen navigation button, including Submit or Finish. Missing personal facts, unsupported controls, invalid plans, or undetected transitions stop the run. This is heuristic discovery: custom widgets, iframe forms, unlabeled questions, and some dynamic layouts need a site adapter. Add a `done` CSS selector to the configuration for reliable completion detection; otherwise the last page can time out. LLM answers are not guaranteed accurate.

## Setup

Run on a desktop or supported Linux environment with Python 3.10+ and Codex CLI installed and signed in (`codex login`). Codex uses its configured authentication and usage limits; this does not connect to an existing chat conversation.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp config.example.json config.json
```

Edit `config.json` with the site's Playwright selectors and your answer instructions. `content` must identify one content container; `answer` identifies one input, textarea, or contenteditable field; `next` identifies one button. `done` identifies a visible completion marker. `identity` identifies a step counter or question ID so identical consecutive questions can be distinguished. Remove optional `identity` or `done` if unavailable. Without a completion marker the app may time out on the last page.

```sh
python runner.py 'https://example.com/start' --config config.json --preview
python runner.py 'https://example.com/another-start' --config config.json --login
```

`--preview` reads and generates once without changing the page. Regular mode fills and clicks automatically, up to `max_pages`. `--login` waits for manual sign-in; browser state persists in `.browser-profile`. `--headless` hides the browser; `--model NAME` overrides Codex's configured model.

The runner detects URL, step identity, or content changes after clicking, including SPA transitions. It stops on repeated pages, oversized input/output, generation errors, or an undetected transition. Clicks are never retried automatically. Error screenshots go to `artifacts/error.png`; answers print to the terminal. Browser profiles and screenshots can contain private data.

Manual selector mode supports one text answer per page in the main frame. Automatic mode supports multiple native fields but cannot guarantee discovery on an arbitrary site. The Codex provider runs a separate CLI process per answer, in a temporary working directory with a read-only sandbox; it inherits local Codex configuration. The instruction to avoid tools is a prompt, not a tool-disabling security boundary.

Android/Termux is not a standard Playwright browser installation target. Run the automation on a supported computer or Linux host if browser installation fails there.

## Checks

```sh
python -m unittest discover -s tests -v
```

A real browser run requires Playwright/Chromium, working selectors, and a signed-in Codex CLI.

## Your response database

`responses.py` keeps your explicitly supplied answers in a local SQLite database at `data/responses.sqlite3`. This directory is excluded from Git. Answers are stored in plain text, not encrypted. Nothing is automatically uploaded or reused by the runner yet.

```sh
python responses.py list
python responses.py add --survey example --key favorite_color --question 'Favorite color?' --answer Blue --scope profile
```

The default `survey` scope applies only to that survey; use `profile` only for facts or preferences you want considered for reuse. Consent should stay survey-specific. Each addition preserves history rather than overwriting earlier answers. A recorded answer does not mean it was submitted to the survey website.

"""Local survey response history. Stores only answers explicitly supplied by you."""
import argparse
import json
from pathlib import Path
import sqlite3

DEFAULT_DB = 'data/responses.sqlite3'


def connect(path=DEFAULT_DB):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY,
            survey TEXT NOT NULL,
            question_key TEXT NOT NULL,
            question TEXT NOT NULL,
            answer_json TEXT NOT NULL,
            scope TEXT NOT NULL CHECK(scope IN ('survey', 'profile')),
            source TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE INDEX IF NOT EXISTS responses_lookup
            ON responses(survey, question_key, id);
    ''')
    return connection


def record(connection, survey, key, question, answer, scope='survey'):
    if not all(isinstance(value, str) and value.strip() for value in (survey, key, question)):
        raise ValueError('Survey, question key, and question are required')
    if not isinstance(answer, (str, list)) or not answer:
        raise ValueError('Answer must be nonempty text or a list of selections')
    if isinstance(answer, list) and any(not isinstance(item, str) or not item.strip() for item in answer):
        raise ValueError('Selections must be nonempty text')
    if isinstance(answer, str) and not answer.strip():
        raise ValueError('Answer must not be blank')
    with connection:
        cursor = connection.execute(
            'INSERT INTO responses(survey, question_key, question, answer_json, scope) VALUES(?,?,?,?,?)',
            (survey, key, question, json.dumps(answer), scope))
    return cursor.lastrowid


def entries(connection):
    result = []
    for row in connection.execute('SELECT * FROM responses ORDER BY id'):
        entry = dict(row)
        entry['answer'] = json.loads(entry.pop('answer_json'))
        result.append(entry)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=DEFAULT_DB)
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('--survey', required=True, help='Survey name or URL without session tokens')
    add.add_argument('--key', required=True)
    add.add_argument('--question', required=True)
    add.add_argument('--answer', required=True, action='append', help='Repeat for multiple selections')
    add.add_argument('--scope', choices=['survey', 'profile'], default='survey')
    commands.add_parser('list')
    args = parser.parse_args()
    connection = connect(args.db)
    try:
        if args.command == 'add':
            answer = args.answer[0] if len(args.answer) == 1 else args.answer
            print(record(connection, args.survey, args.key, args.question, answer, args.scope))
        else:
            print(json.dumps(entries(connection), indent=2, ensure_ascii=False))
    finally:
        connection.close()


if __name__ == '__main__':
    main()

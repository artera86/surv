import json
import unittest
from auto_forms import validate


class AutoFormsTests(unittest.TestCase):
    def setUp(self):
        self.data = {'controls': [
            {'id': '0', 'type': 'radio', 'name': 'choice'},
            {'id': '1', 'type': 'radio', 'name': 'choice'},
            {'id': '2', 'type': 'select', 'options': [{'value': 'a'}]},
            {'id': '3', 'type': 'text'}], 'next': [{'id': '0'}]}

    def plan(self, answers, next_id='0'):
        return validate(json.dumps({'answers': answers, 'next': next_id}), self.data)

    def test_mixed_controls(self):
        result = self.plan([{'id': '0', 'value': True}, {'id': '2', 'value': 'a'}, {'id': '3', 'value': 'hello'}])
        self.assertEqual(len(result['answers']), 3)

    def test_invalid_plans(self):
        for answers in ([], [{'id': 'missing', 'value': 'x'}],
                        [{'id': '0', 'value': 'true'}],
                        [{'id': '0', 'value': True}, {'id': '1', 'value': True}],
                        [{'id': '2', 'value': 'missing'}],
                        [{'id': '3', 'value': 'a'}, {'id': '3', 'value': 'b'}]):
            with self.subTest(answers=answers), self.assertRaises(ValueError):
                self.plan(answers)

    def test_unknown_next(self):
        with self.assertRaises(ValueError):
            self.plan([{'id': '3', 'value': 'hello'}], 'missing')

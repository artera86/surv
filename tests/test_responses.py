import unittest
import responses


class ResponseTests(unittest.TestCase):
    def test_history_and_multiple_selections_round_trip(self):
        connection = responses.connect(':memory:')
        try:
            responses.record(connection, 'demo', 'q1', 'Choose', ['A', 'B'])
            responses.record(connection, 'demo', 'q1', 'Choose', 'C')
            saved = responses.entries(connection)
            self.assertEqual([row['answer'] for row in saved], [['A', 'B'], 'C'])
            self.assertTrue(all(row['scope'] == 'survey' for row in saved))
        finally:
            connection.close()

    def test_blank_answer_is_not_saved(self):
        connection = responses.connect(':memory:')
        try:
            with self.assertRaises(ValueError):
                responses.record(connection, 'demo', 'q1', 'Choose', ' ')
            self.assertEqual(responses.entries(connection), [])
        finally:
            connection.close()

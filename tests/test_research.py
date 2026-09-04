import os
import unittest
from unittest.mock import patch
from lantern.research import Research, openai_research, valid_text


class ResearchTests(unittest.TestCase):
    @patch.dict(os.environ, {'LANTERN_RESEARCH_URL': 'https://example.com/research', 'LANTERN_RESEARCH_TOKEN': 'private'})
    @patch('lantern.research.post')
    def test_consent_and_exact_submission(self, post):
        research = Research()
        with self.assertRaises(ValueError):
            research.start('my reviewed text', False)
        post.assert_not_called()
        post.return_value = {'parts': [{'text': 'Answer', 'citations': []}]}
        research.run('my reviewed text')
        self.assertEqual(post.call_args.args[2], {'text': 'my reviewed text'})
        self.assertNotIn('private', str(research.snapshot()))
        self.assertEqual(research.snapshot()['status'], 'complete')

    @patch.dict(os.environ, {'LANTERN_RESEARCH_URL': 'http://example.com/research', 'LANTERN_RESEARCH_TOKEN': 'private'})
    def test_plaintext_service_rejected(self):
        with self.assertRaises(ValueError):
            Research().start('text', True)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'})
    @patch('lantern.research.post')
    def test_provider_has_search_but_no_execution_tool(self, post):
        post.return_value = {'status': 'completed', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': 'Answer', 'annotations': [
                {'type': 'url_citation', 'url': 'javascript:evil'}]}]}]}
        result = openai_research('untrusted log')
        payload = post.call_args.args[2]
        self.assertFalse(payload['store'])
        self.assertEqual(payload['tools'], [{'type': 'web_search'}])
        self.assertEqual(result['parts'][0]['citations'], [])

    @patch('lantern.research.post', side_effect=RuntimeError('secret provider key'))
    def test_errors_do_not_leak_secrets(self, post):
        research = Research()
        research.run('text')
        self.assertEqual(research.snapshot()['status'], 'failed')
        self.assertNotIn('secret provider key', str(research.snapshot()))

    def test_size_bounds(self):
        for text in ('', ' ' , 'x' * 8001, None):
            with self.assertRaises(ValueError):
                valid_text(text)

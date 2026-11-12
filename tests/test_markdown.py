import unittest

from web_ui.markdown import render_output


class MarkdownTests(unittest.TestCase):
    def test_formats_prose_and_preserves_raw_content(self):
        text = '# Finding\n\n**Risk** in `app.py`.\n\n- Fix it\n\n```python\nx = 1\n```'
        value = {'content': {'parts': [{'text': text}]}}
        html = render_output('LLM OUTPUT', value)
        for tag in ('<h1>', '<strong>', '<code>', '<ul>', '<pre>'):
            self.assertIn(tag, html)
        self.assertEqual(value['content']['parts'][0]['text'], text)
        self.assertIsNone(render_output('TOOL RESULT: read_file', {}))

    def test_untrusted_html_links_and_images_are_inert(self):
        html = render_output('FINAL ANSWER', (
            '<script>alert(1)</script>\n\n'
            '[click](javascript:alert%281%29)\n\n'
            '![image](https://example.com/tracker.png)'
        ))
        self.assertNotIn('<script', html)
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn('<img', html)

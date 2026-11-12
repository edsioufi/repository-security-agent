"""Render model prose without allowing embedded HTML or remote images."""
from markdown_it import MarkdownIt

_parser = MarkdownIt('commonmark', {'html': False}).enable('table')
_parser.disable('image')


def render_output(label, value):
    if label == 'FINAL ANSWER':
        text = value
    elif label == 'LLM OUTPUT':
        content = value.get('content') or {}
        text = '\n'.join(p.get('text', '') for p in content.get('parts', []))
    else:
        return None
    return _parser.render(text) if text else None

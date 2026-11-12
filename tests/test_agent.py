import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from google.adk.tools import FunctionTool

from agent import make_agent
from cli import review
from tests.scripted_model import ScriptedModel
from tools import RepositoryTools


class ToolTests(unittest.TestCase):
    def test_boundaries_and_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.py').write_text('lookup\n' * 100)
            (root / '.env').write_text('private')
            (root / 'secret.txt').write_text('private')
            (root / 'link.py').symlink_to('/etc/passwd')
            tools = RepositoryTools(root)
            self.assertEqual(tools.list_files()['paths'], ['app.py'])
            for path in ['../app.py', '/etc/passwd', '.env', 'link.py']:
                self.assertIn('error', tools.read_file(path))
            result = tools.read_file('app.py', 1, 100)
            self.assertTrue(result['truncated'])
            self.assertEqual(len(result['content'].splitlines()), 80)
            self.assertTrue(tools.search_code('lookup')['truncated'])
            self.assertIn('error', tools.search_code(''))

    def test_bound_method_schema(self):
        tools = RepositoryTools('sample')
        schema = FunctionTool(tools.read_file)._get_declaration()
        fields = schema.parameters_json_schema['properties']
        self.assertEqual(set(fields), {'path', 'start_line', 'end_line'})


class LoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_return_to_model_before_answer(self):
        model = ScriptedModel()
        tools = RepositoryTools('sample')
        agent = make_agent(tools, 'offline', '', model=model)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            success = await review(agent, 'Inspect the sample.')
        self.assertTrue(success)
        self.assertEqual(model._step, 4)
        output = stream.getvalue()
        for name in ['list_files', 'read_file', 'search_code']:
            self.assertIn('TOOL CALL: ' + name, output)
            self.assertIn('TOOL RESULT: ' + name, output)
        answer = output.split('--- FINAL ANSWER ---')[1]
        self.assertIn('return lookup(db, name)', answer)
        self.assertIn('OFFLINE', answer)

    async def test_exhaustion_is_incomplete(self):
        agent = make_agent(
            RepositoryTools('sample'), 'offline', '', model=ScriptedModel(),
        )
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(await review(agent, 'Inspect.', max_calls=1))

import http.client
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import unittest


class WebTests(unittest.TestCase):
    def test_folder_selection_stream_and_request_boundary(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        process = subprocess.Popen(
            [sys.executable, '-c', (
                "import os, web; from offline import ScriptedModel; "
                "os.environ['GEMINI_API_KEY']='test-only'; "
                "original=web.make_agent; "
                "web.make_agent=lambda source,name,key: "
                "original(source,name,key,model=ScriptedModel()); "
                "web.choose_folder=lambda: str(web.Path('sample').resolve()); "
                f"web.serve(port={port})"
            )],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(60):
                try:
                    conn = http.client.HTTPConnection('127.0.0.1', port)
                    conn.request('GET', '/')
                    response = conn.getresponse()
                    page = response.read().decode()
                    break
                except ConnectionError:
                    time.sleep(.1)
            else:
                self.fail('Web server did not start')
            self.assertEqual(response.status, 200)
            self.assertIn('Choose folder', page)
            self.assertNotIn('Offline', page)
            self.assertNotIn('Review question', page)
            token = re.search("'X-Review-Token': '([^']+)'", page)[1]
            headers = {
                'Content-Type': 'application/json',
                'Origin': f'http://127.0.0.1:{port}',
                'X-Review-Token': token,
            }
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
            conn.request('POST', '/review', json.dumps({}),
                         headers | {'Origin': 'https://outside.example'})
            denied = conn.getresponse()
            self.assertEqual(denied.status, 403)
            denied.read()
            for endpoint in ('/folder', '/review'):
                conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
                conn.request('POST', endpoint, '{}', headers | {
                    'X-Review-Token': 'wrong'
                })
                denied = conn.getresponse()
                self.assertEqual(denied.status, 403)
                denied.read()
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
            conn.request('POST', '/folder', '{}', headers)
            selected = conn.getresponse()
            self.assertEqual(selected.status, 200)
            folder = json.loads(selected.read())['path']
            self.assertEqual(folder, str(Path('sample').resolve()))
            for payload in ({}, {'repo': ''}, {'repo': '/nonexistent/repo'},
                            {'repo': folder, 'question': 'override'}):
                conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
                conn.request('POST', '/review', json.dumps(payload), headers)
                invalid = conn.getresponse()
                self.assertEqual(invalid.status, 400)
                invalid.read()
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
            conn.request('POST', '/review', json.dumps({'repo': folder}), headers)
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            events = [json.loads(s) for s in response.read().decode().splitlines()]
            self.assertEqual(events[-1], {'label': 'STATUS', 'value': 'completed'})
            self.assertEqual(sum(e['label'].startswith('TOOL CALL')
                                 for e in events), 3)
            answer = next(e['value'] for e in events
                          if e['label'] == 'FINAL ANSWER')
            self.assertIn('return lookup(db, name)', answer)
        finally:
            process.terminate()
            process.wait(timeout=5)

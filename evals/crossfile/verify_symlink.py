"""Verify pinned CPython path behavior without starting an HTTP server."""
import ast
import os
from pathlib import Path
import posixpath
import tarfile
import tempfile
from types import SimpleNamespace
import urllib.parse


def main():
    with tarfile.open('/tmp/cpython-v3.13.0.tar.gz') as tar:
        code = tar.extractfile('cpython-3.13.0/Lib/http/server.py').read().decode()
    tree = ast.parse(code)
    handler = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                   and n.name == 'SimpleHTTPRequestHandler')
    function = next(n for n in handler.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'translate_path')
    namespace = {'os':os, 'posixpath':posixpath, 'urllib':urllib}
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, 'pinned-translate-path', 'exec'), namespace)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        public = root/'public'
        public.mkdir()
        outside = root/'outside'
        outside.mkdir()
        (outside/'sample.txt').write_text('outside fixture')
        (public/'link').symlink_to(outside, target_is_directory=True)
        translate = namespace['translate_path']
        instance = SimpleNamespace(directory=str(public))
        path = Path(translate(instance, '/link/sample.txt'))
        assert path.read_text() == 'outside fixture'
        assert not path.resolve().is_relative_to(public.resolve())
        ordinary = Path(translate(instance, '/../outside/sample.txt'))
        assert ordinary.is_relative_to(public)
        assert not ordinary.exists()
    print('PASS: pinned translate_path permits symlink resolution outside root;')
    print('ordinary .. components do not escape. No server or network used.')


if __name__ == '__main__':
    main()

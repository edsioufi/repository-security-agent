"""Test only the upstream pure URL predicate, without running rpcapd."""
import json
from pathlib import Path
import subprocess
import tempfile
from evals.crossfile.run import ROOT, load_source


def main():
    m=json.loads((ROOT/'manifest.json').read_text())
    before=load_source('a',m['snapshots']['a']).files['rpcapd/daemon.c']
    after=load_source('b',m['snapshots']['b']).files['rpcapd/daemon.c']
    assert 'if (is_url(source))' not in before
    assert 'if (is_url(source))' in after
    start=after.index('static int\nis_url(const char *source)\n{')
    predicate=after[start:]
    # The upstream predicate is the final function; no network or file APIs.
    program='#include <string.h>\n#include <assert.h>\n'+predicate+'''
int main(void) {
  assert(is_url("rpcap://example.invalid/device") == 1);
  assert(is_url("file://capture") == 1);
  assert(is_url("eth0") == 0);
  assert(is_url("eth0:1") == 0);
  return 0;
}
'''
    with tempfile.TemporaryDirectory() as d:
        source=Path(d)/'guard.c'; source.write_text(program)
        executable=Path(d)/'guard'
        subprocess.run(['cc',str(source),'-o',str(executable)],check=True,capture_output=True)
        subprocess.run([str(executable)],check=True,capture_output=True,timeout=3)
    print('Actual upstream is_url predicate: four assertions passed; no service executed.')


if __name__=='__main__':main()

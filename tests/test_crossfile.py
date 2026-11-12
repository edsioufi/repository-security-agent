import unittest
from types import SimpleNamespace
from evals.crossfile.prepare import strip_comments
from evals.crossfile.run import parse_answer
from evals.crossfile.score import check_evidence


class CrossfileTests(unittest.TestCase):
    def test_comment_filter_keeps_url_literals_and_line_numbers(self):
        raw='/* hint */\nconst char *s="rpcap://host/device"; // hint\n'
        clean=strip_comments(raw)
        self.assertEqual(raw.count('\n'),clean.count('\n'))
        self.assertIn('"rpcap://host/device"',clean)
        self.assertNotIn('hint',clean)

    def test_unseen_real_quote_does_not_count_as_retrieved_evidence(self):
        source=SimpleNamespace(lines=lambda path:['first','second'])
        info={'focal_path':'target.c','start_line':1,'end_line':1}
        item={'path':'target.c','start_line':2,'end_line':2,'quote':'second'}
        record={'answer':{'evidence':[item]},'trace':[]}
        self.assertFalse(check_evidence(record,info,source)[0]['valid_and_seen'])
        item.update(start_line=1,end_line=1,quote='first')
        self.assertTrue(check_evidence(record,info,source)[0]['valid_and_seen'])

    def test_incomplete_answer_not_coerced_to_clean(self):
        with self.assertRaises(ValueError):
            parse_answer('{"verdict":"not_vulnerable"}')

    def test_diff_visibility_excludes_deleted_lines(self):
        from evals.crossfile.score import visible_lines
        record={'scenario':{'name':'pr-current'}, 'trace':[],
                'question':'--- a/x.c\n+++ b/x.c\n@@ -9,2 +9,2 @@\n-old\n+new\n context'}
        self.assertEqual(visible_lines(record,{}), {'x.c':{9,10}})

    def test_whole_source_baseline_has_every_corpus_file(self):
        import json
        from evals.crossfile.run import ROOT
        from evals.crossfile.scenarios import build
        manifest=json.loads((ROOT/'manifest.json').read_text())
        if not (ROOT/'fixtures/a').exists():
            self.skipTest('Pinned source fixtures not downloaded')
        config=build('a','single','large',manifest)
        self.assertEqual(set(config['included_files']),
                         set(manifest['snapshots']['a']['files']))

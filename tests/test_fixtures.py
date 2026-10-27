"""Hand-labelled interpretation cases; labels were written independently."""
import csv, json, pathlib, unittest
from limitaware import canonical, policies

FIX = pathlib.Path(__file__).parent / "fixtures"

class TestLabelledFixtures(unittest.TestCase):
    def test_cases_match_independent_labels(self):
        expected = json.loads((FIX / "expected.json").read_text())
        rows = []
        with (FIX / "interpretation_cases.csv").open(newline="", encoding="utf-8") as fh:
            for i, r in enumerate(csv.DictReader(fh), start=2):
                r["source_row"] = i
                rows.append(r)
        policy = policies.validate(dict(policies.DEFAULT_POLICY))
        records, _ = canonical.transform(rows, policy)
        self.assertEqual(len(records), len(expected))
        # the fixture file and the label file are both ordered by case id
        for case_id, rec in zip(expected.keys(), records):
            want = expected[case_id]
            self.assertEqual(rec["status"], want["status"], case_id)
            self.assertEqual(rec["analysis_eligible"], want["eligible"], case_id)
            if "observation" in want:
                self.assertAlmostEqual(rec["observation"], want["observation"], places=12)

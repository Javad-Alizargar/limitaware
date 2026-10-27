"""Regression tests for the downstream 15-field schema."""
import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from downstream_lib import FIELDS, MalformedOutput, InvalidResult, missing_row, parse_r_output, validate_row

HEADER = "\t".join(FIELDS)
def row(**kw):
    vals = {f: "NA" for f in FIELDS}
    vals.update({"export":"x","policy":"P0","group":"g","n":"100","n_detected":"90",
                 "n_censored":"10","distinct_censoring_limits":"3","median":"0.5",
                 "mean":"1.0","mean_se":"0.1","mean_lcl":"0.8","mean_ucl":"1.2",
                 "fit_status":"ok","warning":"NA","failure_reason":"NA"})
    vals.update(kw); return "\t".join(str(vals[f]) for f in FIELDS)

class TestSchema(unittest.TestCase):
    def test_success_distinct_not_detected(self):
        r = parse_r_output(HEADER+"\n"+row())
        self.assertEqual(r["distinct_censoring_limits"], "3")
        self.assertNotEqual(r["distinct_censoring_limits"], r["n_detected"])
    def test_median_not_identified(self):
        r = parse_r_output(HEADER+"\n"+row(median="NA", fit_status="ok_median_not_identified",
                                          warning="median not identified"))
        self.assertEqual(r["median"], "NA")
    def test_skipped_full_schema(self):
        r = validate_row(missing_row("x","P0","g",7,7,0,0,"skipped_no_censoring","n_censored<1"))
        self.assertEqual(len(r), len(FIELDS)); self.assertEqual(r["fit_status"],"skipped_no_censoring")
    def test_r_error_full_schema(self):
        r = validate_row(missing_row("x","P0","g",100,90,10,3,"r_error","cenfit failed"))
        self.assertEqual(len(r), len(FIELDS)); self.assertEqual(r["fit_status"],"r_error")
    def test_malformed_field_count(self):
        with self.assertRaises(MalformedOutput):
            parse_r_output(HEADER+"\n"+"\t".join(["x"]*14))
    def test_nonfinite(self):
        with self.assertRaises(InvalidResult):
            parse_r_output(HEADER+"\n"+row(mean="inf"))
if __name__ == "__main__": unittest.main()

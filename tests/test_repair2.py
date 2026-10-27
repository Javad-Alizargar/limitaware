"""Regression tests for the 0.1.2 grouped-output and semantics defects."""
from __future__ import annotations
import json, pathlib, tempfile, unittest
from limitaware import canonical, policies, output

BASE = {
    "OrganizationIdentifier": "ORG", "ActivityIdentifier": "ACT-1",
    "ActivityTypeCode": "Sample-Routine", "CharacteristicName": "Atrazine",
    "ResultSampleFractionText": "Total", "ResultMeasureValue": "0.2",
    "ResultMeasure/MeasureUnitCode": "ug/L", "ResultDetectionConditionText": "",
    "MeasureQualifierCode": "", "ResultAnalyticalMethod/MethodIdentifier": "8270C",
    "DetectionQuantitationLimitTypeName": "Reporting limit by DQCALC",
    "DetectionQuantitationLimitMeasure/MeasureValue": "0.1",
    "DetectionQuantitationLimitMeasure/MeasureUnitCode": "ug/L",
}

def row(n=2, **kw):
    d = dict(BASE); d.update(kw); d["source_row"] = n; return d

def pol(**kw):
    p = dict(policies.DEFAULT_POLICY); p.update(kw); return policies.validate(p)

class Test1MixedAnalytes(unittest.TestCase):
    def test_analyte_is_part_of_the_group(self):
        a = row(2, CharacteristicName="Atrazine")
        b = row(3, CharacteristicName="Simazine")
        rec, summary = canonical.transform([a, b], pol())
        self.assertEqual(len(summary["groups"]), 2)
        self.assertNotEqual(rec[0]["analysis_group"], rec[1]["analysis_group"])

class Test2FilenameCollisions(unittest.TestCase):
    def test_names_that_slug_identically_do_not_collide(self):
        a = row(2, **{"ResultAnalyticalMethod/MethodIdentifier": "/"})
        b = row(3, **{"ResultAnalyticalMethod/MethodIdentifier": " "})
        rec, summary = canonical.transform([a, b], pol())
        self.assertEqual(len(summary["groups"]), 2)
        with tempfile.TemporaryDirectory() as d:
            manifest = output.write_analysis(rec, pathlib.Path(d))
            files = [v["file"] for v in manifest["groups"].values()]
            self.assertEqual(len(files), len(set(files)))
            for v in manifest["groups"].values():
                self.assertTrue((pathlib.Path(d) / v["file"]).exists())

class Test3QualifierConflicts(unittest.TestCase):
    def test_right_bound_with_left_code_is_conflict(self):
        rec, _ = canonical.transform([row(ResultMeasureValue=">0.1", MeasureQualifierCode="LT")], pol())
        self.assertEqual(rec[0]["status"], "conflicting_qualifier")
        self.assertFalse(rec[0]["analysis_eligible"])

    def test_left_bound_with_estimated_code_is_conflict_even_if_kept(self):
        for mode in ("exclude", "keep_as_detected"):
            rec, _ = canonical.transform(
                [row(ResultMeasureValue="<0.1", MeasureQualifierCode="J")],
                pol(estimated_results=mode))
            self.assertEqual(rec[0]["status"], "conflicting_qualifier", mode)

class Test4ConversionOverflow(unittest.TestCase):
    def test_overflow_to_infinity_after_conversion_is_rejected(self):
        rec, _ = canonical.transform([row(ResultMeasureValue="1e308",
                                          **{"ResultMeasure/MeasureUnitCode": "ng/l"})],
                                     pol(**{"units": {"target": "ug/L",
                                                      "conversions": {"ug/L": 1.0, "ng/l": 1e308}}}))
        self.assertEqual(rec[0]["status"], "nonfinite_value")
        self.assertFalse(rec[0]["analysis_eligible"])

class Test5JsonDiagnostics(unittest.TestCase):
    def test_ambiguous_limit_report_is_serialisable(self):
        limits = [{"ActivityIdentifier": "ACT-1", "CharacteristicName": "Atrazine",
                   "ResultIdentifier": "R1"}, {"ActivityIdentifier": "ACT-1",
                   "CharacteristicName": "Atrazine", "ResultIdentifier": "R2"}]
        report = canonical.link_limits([row()], limits)
        json.dumps(report)  # must not raise

class Test6DuplicateIdentity(unittest.TestCase):
    def test_duplicate_requires_complete_source_record_match(self):
        a = row(2)
        b = row(3, **{"ResultCommentText": "different"})
        rec, summary = canonical.transform([a, b], pol(duplicates="drop_identical"))
        self.assertEqual(summary["analysis_rows"], 2)

class Test7StaleOutputs(unittest.TestCase):
    def test_rerun_into_non_empty_directory_is_refused_or_clean(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            (out / "analysis.old.csv").write_text("stale")
            with self.assertRaises(Exception):
                output.prepare_outdir(out, force=False)
            output.prepare_outdir(out, force=True)
            self.assertFalse((out / "analysis.old.csv").exists())


class TestManifestReconciliation(unittest.TestCase):
    def test_manifest_entries_match_their_files_exactly(self):
        import csv
        a = row(2, CharacteristicName="Atrazine")
        b = row(3, CharacteristicName="Simazine", **{"ResultAnalyticalMethod/MethodIdentifier": "8141"})
        rec, summary = canonical.transform([a, b], pol())
        with tempfile.TemporaryDirectory() as d:
            manifest = output.write_analysis(rec, pathlib.Path(d))
            seen = set()
            for key, info in manifest["groups"].items():
                path = pathlib.Path(d) / info["file"]
                rows = list(csv.DictReader(path.open()))
                self.assertEqual(len(rows), info["rows"])
                self.assertEqual(sum(1 for r in rows if r["censored"] == "TRUE"), info["censored"])
                for r in rows:
                    seen.add(r["result_uid"])
                group = json.loads(key)
                self.assertEqual({r["analyte"] for r in rows}, {group["analyte"]})
                self.assertEqual({r["method"] for r in rows}, {group["method"]})
            self.assertEqual(seen, {r["result_uid"] for r in rec if r["analysis_eligible"]})


class TestCensoredBlankResultUnit(unittest.TestCase):
    def test_censored_row_uses_limit_unit_when_result_unit_is_blank(self):
        r = row(ResultMeasureValue="", ResultDetectionConditionText="Not Detected",
                **{"ResultMeasure/MeasureUnitCode": "", "DetectionQuantitationLimitTypeName":
                   "Reporting limit by DQCALC", "DetectionQuantitationLimitMeasure/MeasureValue":
                   "100", "DetectionQuantitationLimitMeasure/MeasureUnitCode": "ng/l"})
        rec, _ = canonical.transform([r], pol())
        self.assertEqual(rec[0]["status"], "eligible")
        self.assertAlmostEqual(rec[0]["observation"], 0.1, places=12)
        self.assertEqual(rec[0]["unit"], "ug/L")

    def test_detected_row_with_blank_unit_is_still_rejected(self):
        r = row(ResultMeasureValue="0.5", **{"ResultMeasure/MeasureUnitCode": ""})
        rec, _ = canonical.transform([r], pol())
        self.assertEqual(rec[0]["status"], "unsupported_unit")


class TestUnitRequirements(unittest.TestCase):
    def test_inline_limit_needs_only_the_limit_unit(self):
        r = row(ResultMeasureValue="", ResultDetectionConditionText="Not Detected",
                **{"ResultMeasure/MeasureUnitCode": "",
                   "DetectionQuantitationLimitMeasure/MeasureValue": "100",
                   "DetectionQuantitationLimitMeasure/MeasureUnitCode": "ng/l"})
        rec, _ = canonical.transform([r], pol())
        self.assertEqual(rec[0]["status"], "eligible")
        self.assertAlmostEqual(rec[0]["observation"], 0.1, places=12)

    def test_embedded_bound_needs_the_result_unit(self):
        r = row(ResultMeasureValue="<100", **{"ResultMeasure/MeasureUnitCode": "",
                                              "DetectionQuantitationLimitMeasure/MeasureValue": ""})
        rec, _ = canonical.transform([r], pol())
        self.assertEqual(rec[0]["status"], "unsupported_unit")
        self.assertFalse(rec[0]["analysis_eligible"])

    def test_comparing_bound_and_limit_needs_both_units(self):
        r = row(ResultMeasureValue="<100", **{"ResultMeasure/MeasureUnitCode": "",
                                              "DetectionQuantitationLimitMeasure/MeasureValue": "0.1",
                                              "DetectionQuantitationLimitMeasure/MeasureUnitCode": "ug/L"})
        rec, _ = canonical.transform([r], pol())
        # a missing result unit makes the comparison impossible; the row must not
        # be resolved by choosing one side silently
        self.assertIn(rec[0]["status"], {"unsupported_unit", "conflicting_bound"})
        self.assertFalse(rec[0]["analysis_eligible"])

    def test_detected_value_still_needs_a_result_unit(self):
        r = row(ResultMeasureValue="0.5", **{"ResultMeasure/MeasureUnitCode": ""})
        rec, _ = canonical.transform([r], pol())
        self.assertEqual(rec[0]["status"], "unsupported_unit")

"""Regression tests for independently reproduced defects (added before fixing)."""

from __future__ import annotations

import json
import unittest

from limitaware import canonical, policies

BASE = {
    "OrganizationIdentifier": "ORG-A",
    "ActivityIdentifier": "ACT-1",
    "ActivityTypeCode": "Sample-Routine",
    "CharacteristicName": "Atrazine",
    "ResultSampleFractionText": "Total",
    "ResultMeasureValue": "0.1",
    "ResultMeasure/MeasureUnitCode": "ug/L",
    "ResultDetectionConditionText": "",
    "ResultAnalyticalMethod/MethodIdentifier": "8270C",
    "DetectionQuantitationLimitTypeName": "Reporting limit by DQCALC",
    "DetectionQuantitationLimitMeasure/MeasureValue": "0.1",
    "DetectionQuantitationLimitMeasure/MeasureUnitCode": "ug/L",
}


def row(n=2, **kw):
    d = dict(BASE); d.update(kw); d["source_row"] = n; return d


def pol(**kw):
    p = dict(policies.DEFAULT_POLICY); p.update(kw); return policies.validate(p)


class TestDefect1RightCensored(unittest.TestCase):
    def test_greater_than_is_not_an_exact_detection(self):
        rec, _ = canonical.transform([row(ResultMeasureValue=">0.1")], pol())
        self.assertEqual(rec[0]["status"], "unsupported_right_censored")
        self.assertFalse(rec[0]["analysis_eligible"])
        self.assertIsNone(rec[0]["observation"])


class TestDefect2UnknownQualifier(unittest.TestCase):
    def test_unknown_qualifier_is_unresolved(self):
        rec, _ = canonical.transform([row(MeasureQualifierCode="BANANA")], pol())
        self.assertEqual(rec[0]["status"], "ambiguous_qualifier")
        self.assertIn("qualifier_unknown:BANANA", rec[0]["flags"])


class TestDefect3NonFinite(unittest.TestCase):
    def test_nan_value_is_rejected(self):
        rec, _ = canonical.transform([row(ResultMeasureValue="NaN")], pol())
        self.assertEqual(rec[0]["status"], "nonfinite_value")
        self.assertFalse(rec[0]["analysis_eligible"])

    def test_infinite_limit_is_rejected(self):
        rec, _ = canonical.transform([row(ResultDetectionConditionText="Not Detected",
                                          ResultMeasureValue="",
                                          **{"DetectionQuantitationLimitMeasure/MeasureValue": "inf"})], pol())
        self.assertEqual(rec[0]["status"], "nonfinite_limit")


class TestDefect4BoundConflict(unittest.TestCase):
    def test_embedded_bound_conflicting_with_inline_limit_is_unresolved(self):
        rec, _ = canonical.transform([row(ResultMeasureValue="<0.1",
                                          **{"DetectionQuantitationLimitMeasure/MeasureValue": "0.5"})], pol())
        self.assertEqual(rec[0]["status"], "conflicting_bound")
        self.assertIn("bound_conflict", rec[0]["flags"])
        self.assertIsNone(rec[0]["observation"])

    def test_matching_bound_and_limit_in_different_units_are_accepted(self):
        rec, _ = canonical.transform([row(ResultMeasureValue="<100",
                                          **{"ResultMeasure/MeasureUnitCode": "ng/l"},
                                          **{"DetectionQuantitationLimitMeasure/MeasureValue": "0.1"},
                                          **{"DetectionQuantitationLimitMeasure/MeasureUnitCode": "ug/L"})], pol())
        self.assertEqual(rec[0]["status"], "eligible")
        self.assertAlmostEqual(rec[0]["observation"], 0.1, places=12)


class TestDefect5DuplicateIdentity(unittest.TestCase):
    def test_different_organization_is_not_a_duplicate(self):
        a = row(2)
        b = row(3, OrganizationIdentifier="ORG-B")
        rec, summary = canonical.transform([a, b], pol(duplicates="drop_identical"))
        self.assertEqual(summary["analysis_rows"], 2)

    def test_different_unit_is_not_a_duplicate(self):
        a = row(2)
        b = row(3, **{"ResultMeasure/MeasureUnitCode": "ng/l"}, ResultMeasureValue="100")
        rec, summary = canonical.transform([a, b], pol(duplicates="drop_identical"))
        self.assertEqual(summary["analysis_rows"], 2)

    def test_default_preserves_candidate_duplicates(self):
        rec, summary = canonical.transform([row(2), row(3)], pol())
        self.assertEqual(summary["analysis_rows"], 2)
        self.assertIn("duplicate_preserved", rec[1]["flags"])


class TestDefect6QcKeep(unittest.TestCase):
    def test_qc_keep_actually_keeps(self):
        r = row(ActivityTypeCode="Quality Control Sample-Field Replicate")
        rec, _ = canonical.transform([r], pol(qc_activities="keep"))
        self.assertEqual(rec[0]["status"], "eligible")
        self.assertIn("qc_activity", rec[0]["flags"])


class TestDefect7PolicyValidation(unittest.TestCase):
    def test_zero_negative_and_nonfinite_factors_rejected(self):
        for bad in (0.0, -1.0, float("nan"), float("inf")):
            with self.assertRaises(policies.PolicyError):
                policies.validate({**policies.DEFAULT_POLICY,
                                   "units": {"target": "ug/L", "conversions": {"ug/L": bad}}})

    def test_unknown_schema_version_rejected(self):
        with self.assertRaises(policies.PolicyError):
            policies.validate({**policies.DEFAULT_POLICY, "policy_version": "9.9"})


class TestRepairRequirements(unittest.TestCase):
    def test_estimated_qualifier_not_treated_as_exact(self):
        rec, _ = canonical.transform([row(MeasureQualifierCode="J")], pol())
        self.assertEqual(rec[0]["status"], "excluded_estimated")

    def test_rejected_qualifier_excluded(self):
        rec, _ = canonical.transform([row(MeasureQualifierCode="R")], pol())
        self.assertEqual(rec[0]["status"], "excluded_rejected")

    def test_unknown_condition_is_unresolved(self):
        rec, _ = canonical.transform([row(ResultDetectionConditionText="Something else")], pol())
        self.assertEqual(rec[0]["status"], "ambiguous_condition")

    def test_interval_censored_value_rejected(self):
        rec, _ = canonical.transform([row(ResultMeasureValue="[0.1,0.2]")], pol())
        self.assertEqual(rec[0]["status"], "unsupported_interval_censored")

    def test_analysis_groups_are_separate(self):
        a = row(2)
        b = row(3, **{"ResultAnalyticalMethod/MethodIdentifier": "8141"})
        rec, summary = canonical.transform([a, b], pol())
        self.assertEqual(len(summary["groups"]), 2)
        groups = {json.loads(r["analysis_group"])["method"] for r in rec}
        self.assertEqual(groups, {"8270C", "8141"})

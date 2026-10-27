"""Contract cases derived from the WQX domain value downloads (2026-10-26).

Domain evidence:
  ResultMeasureQualifier code DL: "Not Detected: The analyte was not detected at
  a level >= to the Method Detection Limit for the analysis."
  ResultDetectionCondition "Below Reporting Limit": "data that was found less than
  defined laboratory reporting limits".
  DetectionQuantitationLimitType "Minimum Reporting Level": smallest concentration
  reliably measured; "Estimated Detection Level": detection-level estimate.
"""
from __future__ import annotations
import unittest
from limitaware import canonical, policies

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


class TestWqxDomainContract(unittest.TestCase):
    def test_DL_with_limit_is_censored_not_ambiguous(self):
        rec, _ = canonical.transform([row(
            ResultMeasureValue="", MeasureQualifierCode="DL",
            ResultDetectionConditionText="Not Detected",
            **{"DetectionQuantitationLimitMeasure/MeasureValue": "0.1"})], pol())
        self.assertEqual(rec[0]["status"], "eligible")
        self.assertTrue(rec[0]["censored"])
        self.assertAlmostEqual(rec[0]["observation"], 0.1)

    def test_DL_without_limit_is_refused_as_missing_limit(self):
        rec, _ = canonical.transform([row(
            ResultMeasureValue="0.1", MeasureQualifierCode="DL",
            ResultDetectionConditionText="",
            **{"DetectionQuantitationLimitMeasure/MeasureValue": "",
               "DetectionQuantitationLimitMeasure/MeasureUnitCode": ""})], pol())
        self.assertEqual(rec[0]["status"], "missing_limit")
        self.assertEqual(rec[0]["qualifier_class"], "left_censored")

    def test_below_reporting_limit_condition_is_censored(self):
        rec, _ = canonical.transform([row(
            ResultMeasureValue="", ResultDetectionConditionText="Below Reporting Limit",
            MeasureQualifierCode="U",
            **{"DetectionQuantitationLimitMeasure/MeasureValue": "0.2"})], pol())
        self.assertEqual(rec[0]["status"], "eligible")
        self.assertTrue(rec[0]["censored"])

    def test_minimum_reporting_level_is_a_reporting_limit(self):
        rec, _ = canonical.transform([row(
            DetectionQuantitationLimitTypeName="Minimum Reporting Level")], pol())
        self.assertEqual(rec[0]["limit_role"], "reporting")
        self.assertEqual(rec[0]["status"], "eligible")

    def test_estimated_detection_level_is_a_detection_level(self):
        rec, _ = canonical.transform([row(
            ResultMeasureValue="", ResultDetectionConditionText="Not Detected",
            DetectionQuantitationLimitTypeName="Estimated Detection Level")], pol())
        self.assertEqual(rec[0]["limit_role"], "mdl")
        self.assertEqual(rec[0]["status"], "excluded_limit_role")

    def test_ng_per_L_spelling_converts_identically(self):
        rec, _ = canonical.transform([row(
            ResultMeasureValue="", MeasureQualifierCode="<",
            **{"ResultMeasure/MeasureUnitCode": "ng/L",
               "DetectionQuantitationLimitMeasure/MeasureValue": "200",
               "DetectionQuantitationLimitMeasure/MeasureUnitCode": "ng/L"})], pol())
        self.assertEqual(rec[0]["status"], "eligible")
        self.assertAlmostEqual(rec[0]["observation"], 0.2)


if __name__ == "__main__":
    unittest.main()

"""Core-claim tests for limitaware (stdlib unittest, no R required)."""

from __future__ import annotations

import csv
import pathlib
import subprocess
import sys
import tempfile
import unittest

from limitaware import canonical, contract, policies

BASE_HEADER = {
    "OrganizationIdentifier": "ORG",
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


def row(**overrides) -> dict:
    data = dict(BASE_HEADER)
    data.update(overrides)
    data["source_row"] = data.pop("source_row", 2)
    return data


def policy(**overrides) -> dict:
    p = dict(policies.DEFAULT_POLICY)
    p.update(overrides)
    return policies.validate(p)


class TestContract(unittest.TestCase):
    def test_missing_required_column_is_reported(self):
        header = [c for c in contract.REQUIRED_COLUMNS if c != "DetectionQuantitationLimitTypeName"]
        report = contract.check_columns(header)
        self.assertFalse(report["ok"])
        self.assertEqual(report["missing"], ["DetectionQuantitationLimitTypeName"])

    def test_full_header_passes(self):
        report = contract.check_columns(list(contract.REQUIRED_COLUMNS))
        self.assertTrue(report["ok"])


class TestLinkageAndMultiplication(unittest.TestCase):
    def test_one_output_row_per_input_row(self):
        rows = [row(source_row=2), row(source_row=3, ResultSampleFractionText="Dissolved")]
        records, summary = canonical.transform(rows, policy())
        self.assertEqual(len(records), 2)
        self.assertEqual(summary["rows_in"], summary["rows_out"])

    def test_ambiguous_limit_export_is_not_attached(self):
        limits = [
            {"ActivityIdentifier": "ACT-1", "CharacteristicName": "Atrazine",
             "ResultIdentifier": "R1", "DetectionQuantitationLimitTypeName": "MDL",
             "DetectionQuantitationLimitMeasure/MeasureValue": "0.01"},
            {"ActivityIdentifier": "ACT-1", "CharacteristicName": "Atrazine",
             "ResultIdentifier": "R2", "DetectionQuantitationLimitTypeName": "MDL",
             "DetectionQuantitationLimitMeasure/MeasureValue": "0.02"},
        ]
        report = canonical.link_limits([row()], limits)
        self.assertTrue(report["provided"])
        self.assertEqual(report["ambiguous_keys"],
                         [{"activity": "ACT-1", "analyte": "Atrazine", "limit_records": 2}])
        records, _ = canonical.transform([row()], policy())
        self.assertEqual(records[0]["limit_value"], 0.1)   # inline limit, not a guess

    def test_duplicate_identical_is_flagged_not_merged(self):
        rows = [row(source_row=2), row(source_row=3)]
        records, summary = canonical.transform(rows, policy(duplicates="drop_identical"))
        self.assertEqual(records[0]["status"], "eligible")
        self.assertEqual(records[1]["status"], "duplicate_identical")
        self.assertIn("duplicate_of_row=2", records[1]["status_detail"])
        self.assertEqual(summary["analysis_rows"], 1)


class TestQualifiersAndUnits(unittest.TestCase):
    def test_two_encodings_of_less_than_are_equivalent(self):
        embedded = row(ResultMeasureValue="<0.1", ResultDetectionConditionText="")
        sign_column = row(ResultMeasureValue="", ResultDetectionConditionText="Not Detected")
        a, _ = canonical.transform([embedded], policy())
        b, _ = canonical.transform([sign_column], policy())
        for field in ("censored", "observation", "limit_role"):
            self.assertEqual(a[0][field], b[0][field], field)

    def test_unit_conversion_preserves_value_and_limit(self):
        r = row(ResultMeasureValue="100", **{"ResultMeasure/MeasureUnitCode": "ng/l"},
                **{"DetectionQuantitationLimitMeasure/MeasureValue": "50"},
                **{"DetectionQuantitationLimitMeasure/MeasureUnitCode": "ng/l"},
                ResultDetectionConditionText="")
        records, _ = canonical.transform([r], policy())
        self.assertAlmostEqual(records[0]["value"], 0.1, places=12)
        self.assertAlmostEqual(records[0]["limit_value"], 0.05, places=12)
        self.assertAlmostEqual(records[0]["unit_factor"], 0.001, places=12)

    def test_unsupported_unit_is_flagged(self):
        r = row(**{"ResultMeasure/MeasureUnitCode": "ppt"})
        records, _ = canonical.transform([r], policy())
        self.assertEqual(records[0]["status"], "unsupported_unit")
        self.assertFalse(records[0]["analysis_eligible"])


class TestPolicies(unittest.TestCase):
    def test_limit_roles_are_not_interchangeable(self):
        mdl = row(DetectionQuantitationLimitTypeName="Method Detection Level",
                  ResultMeasureValue="", ResultDetectionConditionText="Not Detected")
        strict, _ = canonical.transform([mdl], policy())
        broad, _ = canonical.transform([mdl], policy(
            censoring_limit_roles=["reporting", "mdl"]))
        self.assertEqual(strict[0]["status"], "excluded_limit_role")
        self.assertEqual(broad[0]["status"], "eligible")

    def test_fraction_separation(self):
        r = row(ResultSampleFractionText="Dissolved")
        records, _ = canonical.transform([r], policy())
        self.assertEqual(records[0]["status"], "excluded_fraction")

    def test_below_loq_policy(self):
        r = row(ResultDetectionConditionText="Present Below Quantification Limit",
                ResultMeasureValue="0.05")
        excluded, _ = canonical.transform([r], policy(below_loq="exclude"))
        kept, _ = canonical.transform([r], policy(below_loq="keep_as_detected"))
        self.assertEqual(excluded[0]["status"], "excluded_below_loq")
        self.assertEqual(kept[0]["status"], "eligible")
        self.assertFalse(kept[0]["censored"])

    def test_missing_limit_for_censored_is_unresolved(self):
        r = row(ResultMeasureValue="", ResultDetectionConditionText="Not Detected",
                **{"DetectionQuantitationLimitMeasure/MeasureValue": ""})
        records, _ = canonical.transform([r], policy())
        self.assertEqual(records[0]["status"], "missing_limit")
        self.assertEqual(records[0]["status_detail"], "censored result without a limit")

    def test_detected_without_limit_is_allowed_by_default(self):
        r = row(**{"DetectionQuantitationLimitMeasure/MeasureValue": ""})
        records, _ = canonical.transform([r], policy())
        self.assertEqual(records[0]["status"], "eligible")
        self.assertFalse(records[0]["censored"])

    def test_policy_validation_rejects_unknown_role(self):
        with self.assertRaises(policies.PolicyError):
            policies.validate({**policies.DEFAULT_POLICY,
                               "censoring_limit_roles": ["banana"]})


class TestReconciliationAndDeterminism(unittest.TestCase):
    def test_every_input_row_reconciles_to_one_status(self):
        rows = [row(source_row=2), row(source_row=3, ResultSampleFractionText="Dissolved"),
                row(source_row=4, ResultMeasureValue="", ResultDetectionConditionText="Not Detected",
                    **{"DetectionQuantitationLimitMeasure/MeasureValue": ""})]
        records, summary = canonical.transform(rows, policy())
        self.assertEqual([r["source_row"] for r in records], [2, 3, 4])
        self.assertEqual(sum(summary["status_counts"].values()), len(rows))

    def test_deterministic_rerun(self):
        rows = [row(source_row=2), row(source_row=3)]
        a, _ = canonical.transform(rows, policy())
        b, _ = canonical.transform(rows, policy())
        self.assertEqual(a, b)

    def test_duplicate_kept_when_policy_says_keep(self):
        rows = [row(source_row=2), row(source_row=3)]
        records, summary = canonical.transform(rows, policy(duplicates="keep"))
        self.assertEqual(summary["analysis_rows"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestBelowLoqWithoutValue(unittest.TestCase):
    def test_below_loq_without_value_is_unresolved_under_both_policies(self):
        r = row(ResultDetectionConditionText="Present Below Quantification Limit",
                ResultMeasureValue="")
        excluded, _ = canonical.transform([r], policy(below_loq="exclude"))
        self.assertEqual(excluded[0]["status"], "excluded_below_loq")
        kept, _ = canonical.transform([r], policy(below_loq="keep_as_detected"))
        self.assertEqual(kept[0]["status"], "ambiguous_missing_value")
        self.assertEqual(kept[0]["observation"], None)


class TestDiagnosticFlags(unittest.TestCase):
    def test_multiple_problems_are_all_retained(self):
        r = row(ActivityTypeCode="Quality Control Sample-Field Replicate",
                ResultSampleFractionText="Dissolved",
                **{"ResultMeasure/MeasureUnitCode": "ppt"})
        records, _ = canonical.transform([r], policy())
        self.assertEqual(records[0]["status"], "excluded_qc")   # primary
        flags = records[0]["flags"]
        self.assertIn("qc_activity", flags)
        self.assertIn("fraction_not_admissible:Dissolved", flags)
        self.assertIn("unit_unconvertible:ppt", flags)

    def test_detected_without_limit_is_flagged_but_eligible(self):
        r = row(**{"DetectionQuantitationLimitMeasure/MeasureValue": ""})
        records, _ = canonical.transform([r], policy())
        self.assertEqual(records[0]["status"], "eligible")
        self.assertIn("detected_without_limit", records[0]["flags"])

    def test_unknown_limit_type_is_flagged(self):
        r = row(ResultMeasureValue="", ResultDetectionConditionText="Not Detected",
                DetectionQuantitationLimitTypeName="Practical Quantitation Limit")
        records, _ = canonical.transform([r], policy(censoring_limit_roles=["reporting", "unknown"]))
        self.assertIn("limit_type_unknown:Practical Quantitation Limit", records[0]["flags"])


class TestResultUidScope(unittest.TestCase):
    def test_uid_is_source_instance_specific(self):
        """result_uid includes the source row, so reordering changes it."""
        a, _ = canonical.transform([row(source_row=2), row(source_row=3)], policy())
        b, _ = canonical.transform([row(source_row=5), row(source_row=6)], policy())
        self.assertNotEqual(a[0]["result_uid"], b[0]["result_uid"])
        self.assertNotEqual(a[0]["result_uid"], a[1]["result_uid"])


class TestHashGuard(unittest.TestCase):
    def test_hash_mismatch_is_rejected(self):
        import tempfile, pathlib
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write("a,b\n1,2\n")
            path = fh.name
        with self.assertRaises(contract.ContractError):
            contract.verify_hash(path, "0" * 64)
        actual = contract.verify_hash(path, None)
        self.assertEqual(len(actual), 64)
        pathlib.Path(path).unlink()

"""Input contract for the WQP Result CSV (LimitAware v0.1).

The contract is deliberately narrow: one file, one profile, one row per result.
"""

from __future__ import annotations

import csv
import hashlib
import pathlib

CONTRACT_VERSION = "wqp-result-csv/2026-10"


class ContractError(ValueError):
    """Raised when an export does not satisfy the frozen input contract."""

#: columns without which the export cannot be interpreted
REQUIRED_COLUMNS = [
    "OrganizationIdentifier",
    "ActivityIdentifier",
    "ActivityTypeCode",
    "CharacteristicName",
    "ResultSampleFractionText",
    "ResultMeasureValue",
    "ResultMeasure/MeasureUnitCode",
    "ResultDetectionConditionText",
    "ResultAnalyticalMethod/MethodIdentifier",
    "DetectionQuantitationLimitTypeName",
    "DetectionQuantitationLimitMeasure/MeasureValue",
    "DetectionQuantitationLimitMeasure/MeasureUnitCode",
]

#: columns used when present but not required for interpretation
OPTIONAL_COLUMNS = [
    "OrganizationFormalName", "ActivityMediaName", "ActivityStartDate",
    "ResultStatusIdentifier", "ResultValueTypeName", "MeasureQualifierCode",
    "ResultLaboratoryCommentText", "ResultCommentText", "ActivityCommentText",
    "ResultAnalyticalMethod/MethodName",
]

CONTRACT_NOTES = [
    "The WQP Result CSV carries the detection/quantitation limit INLINE on the "
    "result row; a separate limits export is therefore not required.",
    "The Result CSV does NOT contain ResultIdentifier, and neither does the XML "
    "profile tested here. A separate ResultDetectionQuantitationLimit export "
    "cannot be joined unambiguously and is only used for consistency checks.",
    "One row is one reported result. Rows are not deduplicated unless the policy "
    "says so, and any drop is recorded with the row number of the kept record.",
]


def sha256(path: str | pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_hash(path: str | pathlib.Path, expected: str) -> str:
    """Return the actual digest; raise if it differs from ``expected``.

    A fetch script cannot guarantee future reproduction: the portal may revise an
    export. Callers must pass the expected digest explicitly and decide how to
    proceed when it no longer matches.
    """
    actual = sha256(path)
    if expected and actual.lower() != expected.lower():
        raise ContractError(
            f"input hash mismatch: expected {expected[:16]}..., got {actual[:16]}...; "
            "the portal export may have been revised - re-inspect before using the "
            "stored policy")
    return actual


def read_rows(path: str | pathlib.Path) -> tuple[list[dict], list[str]]:
    """Return (rows with a 1-based ``source_row``, header)."""
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = []
        for i, row in enumerate(reader, start=2):
            row["source_row"] = i
            rows.append(row)
    return rows, header


def check_columns(header: list[str]) -> dict:
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    return {
        "contract_version": CONTRACT_VERSION,
        "columns_total": len(header),
        "required_present": len(REQUIRED_COLUMNS) - len(missing),
        "required_total": len(REQUIRED_COLUMNS),
        "missing": missing,
        "ok": not missing,
        "optional_present": [c for c in OPTIONAL_COLUMNS if c in header],
    }

#!/usr/bin/env python3
"""Independent, competent preparation baseline (written from the same docs).

This script does not import or copy LimitAware code. It implements the same task
with ordinary Python: validate columns, interpret qualifiers/conditions, convert
units, apply the reporting-limit policy, group by analyte/fraction/method, and
write per-group CSVs plus an audit record.

Usage:
    python baseline_prepare.py INPUT.csv OUTDIR [CONFIG.json]

The optional config sets the same knobs as the LimitAware policy: fraction,
admissible methods, value-type filtering, duplicate handling, estimated results,
below-LOQ handling and admissible limit roles.
"""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import sys

REQUIRED = ["ActivityIdentifier", "ActivityTypeCode", "CharacteristicName",
            "ResultSampleFractionText", "ResultMeasureValue",
            "ResultMeasure/MeasureUnitCode", "ResultDetectionConditionText",
            "MeasureQualifierCode", "ResultAnalyticalMethod/MethodIdentifier",
            "DetectionQuantitationLimitTypeName",
            "DetectionQuantitationLimitMeasure/MeasureValue",
            "DetectionQuantitationLimitMeasure/MeasureUnitCode"]

REPORT_TYPES = {"reporting limit by dqcalc", "lower reporting limit",
                "laboratory reporting level", "minimum reporting level"}
UNITS = {"ug/l": 1.0, "ug/L": 1.0, "ng/l": 0.001, "ng/L": 0.001}
TARGET = "ug/L"
LEFT_Q = ("<", "LT", "U", "ND", "DL")
ND_CONDS = {"not detected", "below reporting limit",
            "not detected at detection limit", "not detected at reporting limit"}


def num(text):
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


DEFAULT_CONFIG = {
    "admissible_fractions": ["Total"],
    "admissible_methods": None,
    "require_actual_value_type": True,
    "duplicates": "keep",
    "estimated_results": "exclude",
    "below_loq": "exclude",
    "limit_roles": ["reporting"],
    "qc": "exclude",
}


def main(inp: str, outdir: str, config_path: str | None = None) -> int:
    src = pathlib.Path(inp)
    out = pathlib.Path(outdir)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to write into non-empty directory {out}")
    out.mkdir(parents=True, exist_ok=True)

    cfg = dict(DEFAULT_CONFIG)
    if config_path:
        cfg.update(json.loads(pathlib.Path(config_path).read_text()))
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    rows = []
    with src.open(encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"missing columns: {missing}")
        for i, row in enumerate(reader, start=2):
            row["_row"] = i
            rows.append(row)

    prepared, groups, seen = [], {}, {}
    for row in rows:
        g = lambda k: (row.get(k) or "").strip()
        val, limit = num(g("ResultMeasureValue")), num(g("DetectionQuantitationLimitMeasure/MeasureValue"))
        funit, lunit = UNITS.get(g("ResultMeasure/MeasureUnitCode")), UNITS.get(g("DetectionQuantitationLimitMeasure/MeasureUnitCode"))
        qual = g("MeasureQualifierCode").upper()
        cond = g("ResultDetectionConditionText").lower()
        status = "eligible"
        activity = g("ActivityTypeCode")
        if cfg["require_actual_value_type"] and g("ResultValueTypeName") and g("ResultValueTypeName").lower() != "actual":
            status = "excluded_value_type"
        elif cfg["qc"] == "exclude" and (activity.startswith("Quality Control") or activity == "Field Msr/Obs"):
            status = "excluded_qc"
        elif g("ResultSampleFractionText") not in cfg["admissible_fractions"]:
            status = "excluded_fraction"
        elif val is not None and funit is None:
            status = "unsupported_unit"
        elif qual == "J" and cfg["estimated_results"] == "exclude":
            status = "excluded_estimated"
        elif qual and qual not in ("<", "LT", "U", "ND", "DL", ">", "GT", "R", "X"):
            status = "ambiguous_qualifier"
        elif qual in (">", "GT") or g("ResultMeasureValue").startswith(">"):
            status = "unsupported_right_censored"
        else:
            censored = cond in ND_CONDS or qual in LEFT_Q
            if censored:
                if limit is None:
                    status = "missing_limit"
                elif lunit is None:
                    status = "unsupported_limit_unit"
                elif g("DetectionQuantitationLimitTypeName").lower() not in REPORT_TYPES:
                    status = "excluded_limit_role"
                else:
                    prepared_value = limit * lunit
                    status = "eligible"
            elif cond == "present below quantification limit" and cfg["below_loq"] == "exclude":
                status = "excluded_below_loq"      # policy: exclude below-LOQ results
            elif val is not None and funit is not None:
                status = "eligible"
            elif val is None:
                status = "ambiguous_missing_value"
            else:
                status = "ambiguous_missing_value"
        is_cens = cond in ND_CONDS or qual in LEFT_Q
        rec = {"row": row["_row"], "analyte": g("CharacteristicName"),
               "fraction": g("ResultSampleFractionText"), "method": g("ResultAnalyticalMethod/MethodIdentifier"),
               "status": status,
               "obs": (limit * lunit) if status == "eligible" and is_cens else
                      ((val * funit) if status == "eligible" and val is not None and funit is not None else None),
               "censored": is_cens,
               "digest": digest}
        seen_key = tuple(sorted((k, str(v)) for k, v in row.items() if k != "_row"))
        if status == "eligible" and cfg["duplicates"] == "drop_identical" and seen_key in seen:
            status = "duplicate_identical"; rec["status"] = status; rec["obs"] = None
        seen.setdefault(seen_key, row["_row"])
        prepared.append(rec)
        if status == "eligible":
            key = (rec["analyte"], rec["fraction"], rec["method"])
            groups.setdefault(key, []).append(rec)

    with (out / "prepared.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(prepared[0].keys())); w.writeheader(); w.writerows(prepared)
    manifest = {}
    for key, members in groups.items():
        slug = "__".join(re.sub(r"[^A-Za-z0-9._-]+", "_", x) for x in key)
        suffix = hashlib.sha1("|".join(key).encode("utf-8")).hexdigest()[:8]
        name = f"prepared__{slug}.{suffix}.csv"
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["obs", "censored", "row", "digest"])
            w.writeheader()
            for m in members:
                w.writerow({"obs": m["obs"], "censored": "TRUE" if m["censored"] else "FALSE",
                            "row": m["row"], "digest": m["digest"]})
        manifest["|".join(key)] = {"file": name, "rows": len(members),
                                   "censored": sum(1 for m in members if m["censored"])}
    counts = {}
    for r in prepared:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    (out / "audit.json").write_text(json.dumps({
        "input": src.name, "sha256": digest, "rows": len(prepared),
        "status_counts": counts, "groups": manifest,
        "policy": cfg,
    }, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(prepared), "status_counts": counts,
                      "groups": manifest}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))

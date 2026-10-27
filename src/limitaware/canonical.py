"""Canonical representation, eligibility rules and limit linkage.

Four layers are kept distinct: raw content, parsed meaning, eligibility, and
policy-dependent censoring. Every source row gets exactly one status and may carry
several diagnostic flags. Nothing is dropped or repaired silently.
"""

from __future__ import annotations

import hashlib
import json
import math

LIMIT_ROLE = {
    "method detection level": "mdl",
    "method detection limit (mdl)": "mdl",
    "reporting limit by dqcalc": "reporting",
    "lower reporting limit": "reporting",
    "laboratory reporting level": "reporting",
    "lower quantitation limit": "loq",
    "elevated detection limit": "other",
    "minimum reporting level": "reporting",
    "estimated detection level": "mdl",
    "long term method detection level": "mdl",
    "long term method detection limit": "mdl",
}

#: qualifier meanings; anything else is unknown and must not be treated as exact
QUALIFIER_CLASS = {
    "<": "left_censored",
    "LT": "left_censored",
    "U": "left_censored",
    "ND": "left_censored",
    ">": "right_censored",
    "GT": "right_censored",
    "J": "estimated",
    "R": "rejected",
    "X": "rejected",
    "DL": "left_censored",       # WQX domain: not detected at/above the MDL
}

NON_DETECT_CONDITIONS = {
    "not detected",
    "below reporting limit",
    "not detected at detection limit",
    "not detected at reporting limit",
}
KNOWN_CONDITIONS = {"", "present below quantification limit", "present",
                    "detected"} | NON_DETECT_CONDITIONS

GENERATED_FIELDS = {"source_row", "result_uid", "source_sha256", "__row__", "observation"}

LEFT_CODES = {"<", "LT", "U", "ND", "DL"}
RIGHT_CODES = {">", "GT"}
ESTIMATED_CODES = {"J"}
REJECTED_CODES = {"R", "X"}


def group_of(row: dict) -> dict:
    """Structured analysis group: analyte, fraction and method are all identity."""
    return {
        "analyte": (row.get("CharacteristicName") or "").strip(),
        "fraction": (row.get("ResultSampleFractionText") or "").strip(),
        "method": (row.get("ResultAnalyticalMethod/MethodIdentifier") or "").strip(),
    }


def result_uid(row: dict) -> str:
    key = "\x1f".join([row.get("OrganizationIdentifier", ""),
                        str(row.get("source_row", ""))])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def duplicate_key(row: dict) -> tuple:
    """Identity = the complete source record, excluding generated provenance.

    Comparing every source column (order-independent) means two rows are only
    "identical" when nothing in the delivered record differs. Generated fields
    (row number, uid, digest, parsed observation) are excluded.
    """
    return tuple(sorted((k, str(v)) for k, v in row.items()
                        if k not in GENERATED_FIELDS))


def _number(text: str) -> float | None:
    text = (text or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _nonfinite(text: str) -> bool:
    value = _number(text)
    return value is not None and not math.isfinite(value)


def _interval(text: str) -> bool:
    text = (text or "").strip()
    return len(text) >= 2 and text[0] in "[(" and text[-1] in "])"


def parse_measurement(row: dict, policy: dict) -> dict:
    """Parse one raw row into meaning; eligibility is decided by ``classify``."""
    cond = (row.get("ResultDetectionConditionText") or "").strip()
    raw_value = (row.get("ResultMeasureValue") or "").strip()
    qualifier = (row.get("MeasureQualifierCode") or "").strip()
    raw_unit = (row.get("ResultMeasure/MeasureUnitCode") or "").strip()
    raw_limit = (row.get("DetectionQuantitationLimitMeasure/MeasureValue") or "").strip()
    limit_unit = (row.get("DetectionQuantitationLimitMeasure/MeasureUnitCode") or "").strip()
    limit_type_raw = (row.get("DetectionQuantitationLimitTypeName") or "").strip()
    role = LIMIT_ROLE.get(limit_type_raw.lower(), "unknown" if limit_type_raw else "")
    conversions = policy["units"]["conversions"]
    target = policy["units"]["target"]
    factor = conversions.get(raw_unit)
    limit_factor = conversions.get(limit_unit)

    interval = _interval(raw_value)
    embedded = ""
    numeric_text = raw_value
    if not interval and raw_value[:1] in ("<", ">"):
        embedded, numeric_text = raw_value[0], raw_value[1:].strip()

    value = _number(numeric_text)
    limit = _number(raw_limit)
    value_nonfinite = _nonfinite(numeric_text) if value is not None else False
    limit_nonfinite = _nonfinite(raw_limit) if limit is not None else False
    embedded_bound = _number(numeric_text) if embedded else None

    # compare an embedded bound with the inline limit in the same unit
    bound_conflict = False
    bound_delta = None
    if embedded and embedded_bound is not None and limit is not None:
        if factor is None or limit_factor is None:
            bound_conflict = True
        else:
            a = embedded_bound * factor
            b = limit * limit_factor
            bound_delta = abs(a - b)
            scale = max(abs(a), abs(b), 1e-30)
            bound_conflict = bound_delta > policy["boundary_tolerance"] * scale
    # if only the embedded bound is present, it becomes the censoring threshold
    limit_source = "inline" if limit is not None else ("embedded" if embedded_bound is not None else "")
    if limit is None and embedded_bound is not None and factor is not None:
        limit = embedded_bound * factor
        limit_unit = target
        limit_factor = 1.0

    if value is not None and factor is not None:
        value *= factor
        if not math.isfinite(value):
            value = None
            value_nonfinite = True
    if limit is not None and limit_factor is not None:
        limit *= limit_factor
        if not math.isfinite(limit):
            limit = None
            limit_nonfinite = True

    # ---- explicit qualifier conflict table -----------------------------
    upper = qualifier.upper()
    coded = ("left" if upper in LEFT_CODES else
             "right" if upper in RIGHT_CODES else
             "estimated" if upper in ESTIMATED_CODES else
             "rejected" if upper in REJECTED_CODES else
             "unknown" if qualifier else "")
    embedded_class = "left" if embedded == "<" else ("right" if embedded == ">" else "")
    conflict = ""
    if embedded_class and coded:
        cls = embedded_class if embedded_class == coded else "conflict"
        if cls == "conflict":
            conflict = f"embedded {embedded!r} vs coded {qualifier!r}"
    elif embedded_class:
        cls = embedded_class
    elif coded:
        cls = coded
    else:
        cls = ""
    if cond.lower() in NON_DETECT_CONDITIONS:
        if cls in ("right", "estimated", "rejected"):
            conflict = conflict or f"'Not Detected' with {cls} evidence"
            cls = "conflict"
        elif cls == "":
            cls = "left"
    qclass = {"": "", "left": "left_censored", "right": "right_censored",
              "estimated": "estimated", "rejected": "rejected",
              "unknown": "unknown", "conflict": "conflicting_qualifier"}[cls]
    censored = qclass == "left_censored"

    return {
        "condition_raw": cond,
        "qualifier_raw": qualifier,
        "qualifier_class": qclass,
        "embedded_qualifier": embedded,
        "interval_value": interval,
        "value_raw": raw_value,
        "value": value,
        "value_nonfinite": value_nonfinite,
        "unit_raw": raw_unit,
        "unit": target if (factor is not None or (censored and limit_factor is not None)) else "",
        "unit_factor": factor,
        "censored": censored,
        "limit_raw": raw_limit,
        "limit_value": limit,
        "limit_nonfinite": limit_nonfinite,
        "limit_unit_raw": limit_unit,
        "limit_factor": limit_factor,
        "limit_type_raw": limit_type_raw,
        "limit_role": role,
        "limit_source": limit_source,
        "bound_conflict": bound_conflict,
        "bound_delta": bound_delta,
        "analysis_group": json.dumps(group_of(row), sort_keys=True),
    }


def classify(row: dict, parsed: dict, policy: dict, seen: dict) -> tuple[str, str, list[str]]:
    """Return (status, detail, flags). Flags are independent of the status."""
    flags: list[str] = []
    activity = (row.get("ActivityTypeCode") or "").strip()
    fraction = (row.get("ResultSampleFractionText") or "").strip()
    method = (row.get("ResultAnalyticalMethod/MethodIdentifier") or "").strip()
    value_type = (row.get("ResultValueTypeName") or "").strip()
    cond = parsed["condition_raw"].lower()
    qclass = parsed["qualifier_class"]

    # ---- diagnostic flags -------------------------------------------------
    if activity.startswith("Quality Control"):
        flags.append("qc_activity")
    if activity == "Field Msr/Obs":
        flags.append("field_measurement")
    if fraction not in policy["admissible_fractions"]:
        flags.append(f"fraction_not_admissible:{fraction or 'missing'}")
    allowed_methods = policy.get("admissible_methods")
    if allowed_methods and method not in allowed_methods:
        flags.append(f"method_not_admissible:{method or 'missing'}")
    if value_type and value_type.lower() != "actual":
        flags.append(f"value_type_not_actual:{value_type}")
    if parsed["unit_factor"] is None:
        flags.append(f"unit_unconvertible:{parsed['unit_raw'] or 'missing'}")
    if parsed["censored"] and parsed["limit_value"] is None:
        flags.append("limit_missing")
    if parsed["limit_type_raw"] and parsed["limit_role"] == "unknown":
        flags.append(f"limit_type_unknown:{parsed['limit_type_raw']}")
    if parsed["censored"] and parsed["limit_role"] not in policy["censoring_limit_roles"]:
        flags.append(f"limit_role_not_admissible:{parsed['limit_role'] or 'missing'}")
    if cond == "present below quantification limit":
        flags.append("below_loq")
    if qclass == "estimated":
        flags.append("estimated_result")
    if qclass == "right_censored":
        flags.append("right_censored")
    if qclass == "rejected":
        flags.append("rejected_result")
    if qclass == "unknown":
        flags.append(f"qualifier_unknown:{parsed['qualifier_raw']}")
    if qclass == "conflicting_qualifier":
        flags.append(f"qualifier_conflict:{parsed['qualifier_raw']}")
    if parsed["bound_conflict"]:
        flags.append("bound_conflict")
    if parsed["value_nonfinite"]:
        flags.append("nonfinite_value")
    if parsed["limit_nonfinite"]:
        flags.append("nonfinite_limit")
    if parsed["interval_value"]:
        flags.append("interval_censored")
    if cond and cond not in KNOWN_CONDITIONS:
        flags.append(f"condition_unknown:{parsed['condition_raw']}")
    is_duplicate = duplicate_key(row) in seen
    if is_duplicate:
        flags.append(f"exact_duplicate_of_row:{seen[duplicate_key(row)]}")
        if policy["duplicates"] == "keep":
            flags.append("duplicate_preserved")
    if not parsed["censored"] and parsed["value"] is not None and parsed["limit_value"] is None:
        flags.append("detected_without_limit")

    # ---- primary status (documented precedence) ---------------------------
    if parsed["interval_value"]:
        return "unsupported_interval_censored", "interval-censored value", flags
    if qclass == "right_censored":
        return "unsupported_right_censored", "right-censored value not usable in left-censored analysis", flags
    if qclass == "unknown":
        return "ambiguous_qualifier", f"unknown qualifier {parsed['qualifier_raw']!r}", flags
    if qclass == "conflicting_qualifier":
        return "conflicting_qualifier", "embedded and coded qualifiers disagree", flags
    if qclass == "rejected":
        return "excluded_rejected", "result flagged as rejected", flags
    if qclass == "estimated":
        if policy["estimated_results"] == "keep_as_detected":
            flags.append("estimated_kept_by_policy")
        else:
            return "excluded_estimated", "estimated value excluded by policy", flags

    qc = activity.startswith("Quality Control") or activity == "Field Msr/Obs"
    if qc and policy["qc_activities"] == "exclude":
        return "excluded_qc", f"activity_type={activity}", flags
    if fraction not in policy["admissible_fractions"]:
        return "excluded_fraction", f"fraction={fraction or 'missing'}", flags
    if allowed_methods and method not in allowed_methods:
        return "excluded_method", f"method={method or 'missing'}", flags
    if value_type and value_type.lower() != "actual":
        return "excluded_value_type", f"value_type={value_type}", flags
    # Unit requirements follow the evidence actually used:
    #   numeric result              -> result unit required
    #   embedded bound (e.g. "<0.1")-> result unit required (the bound is in result units)
    #   inline limit only            -> limit unit required, result unit not needed
    needs_result_unit = (parsed["value"] is not None
                         or parsed["limit_source"] == "embedded")
    if needs_result_unit and parsed["unit_factor"] is None:
        return "unsupported_unit", f"unit={parsed['unit_raw'] or 'missing'}", flags
    if parsed["value_nonfinite"]:
        return "nonfinite_value", "non-finite result value", flags
    if parsed["limit_nonfinite"]:
        return "nonfinite_limit", "non-finite limit value", flags
    if parsed["bound_conflict"]:
        return "conflicting_bound", "embedded bound and inline limit disagree", flags
    if is_duplicate and policy["duplicates"] == "drop_identical":
        return "duplicate_identical", f"duplicate_of_row={seen[duplicate_key(row)]}", flags
    if cond and cond not in KNOWN_CONDITIONS:
        return "ambiguous_condition", f"condition={parsed['condition_raw']}", flags
    if parsed["censored"]:
        if parsed["limit_value"] is None:
            return "missing_limit", "censored result without a limit", flags
        if parsed["limit_factor"] is None:
            return "unsupported_limit_unit", f"limit_unit={parsed['limit_unit_raw'] or 'missing'}", flags
        if parsed["limit_role"] not in policy["censoring_limit_roles"]:
            return "excluded_limit_role", f"limit_role={parsed['limit_role'] or 'missing'}", flags
        return "eligible", f"censored at limit ({parsed['limit_source']})", flags
    if parsed["value"] is None:
        if cond == "present below quantification limit":
            if policy["below_loq"] == "keep_as_detected":
                return "ambiguous_missing_value", "below-LOQ without a reported value", flags
            return "excluded_below_loq", "below-LOQ excluded by policy", flags
        return "ambiguous_missing_value", f"condition={parsed['condition_raw'] or 'missing'}", flags
    if cond == "present below quantification limit":
        if policy["below_loq"] == "keep_as_detected":
            return "eligible", "below-LOQ kept as reported value (policy)", flags
        return "excluded_below_loq", "below-LOQ excluded by policy", flags
    if parsed["limit_value"] is None and policy["treat_missing_limit_for_detected"] == "require":
        return "missing_limit", "detected result requires a limit by policy", flags
    return "eligible", "detected value", flags


def link_limits(rows: list[dict], limits_rows: list[dict] | None) -> dict:
    if not limits_rows:
        return {"provided": False}
    index: dict[tuple, list[dict]] = {}
    for limit in limits_rows:
        key = (limit.get("ActivityIdentifier", ""), limit.get("CharacteristicName", ""))
        index.setdefault(key, []).append(limit)
    ambiguous = [{"activity": k[0], "analyte": k[1], "limit_records": len(v)}
                 for k, v in sorted(index.items()) if len(v) > 1]
    return {"provided": True, "limit_records": len(limits_rows),
            "keys": len(index), "ambiguous_keys": ambiguous}


def transform(rows: list[dict], policy: dict) -> tuple[list[dict], dict]:
    """Return (canonical rows, summary). One output row per input row."""
    canonical: list[dict] = []
    seen: dict[tuple, int] = {}
    counts: dict[str, int] = {}
    groups: dict[str, int] = {}

    for row in rows:
        parsed = parse_measurement(row, policy)
        # register identity before classification so duplicates can be flagged
        key = duplicate_key(row)
        status, detail, flags = classify(row, parsed, policy, seen)
        if key not in seen:
            seen[key] = int(row["source_row"])
        record = {
            "source_row": row["source_row"],
            "result_uid": result_uid(row),
            "organization": row.get("OrganizationIdentifier", ""),
            "activity_id": row.get("ActivityIdentifier", ""),
            "activity_type": row.get("ActivityTypeCode", ""),
            "activity_date": row.get("ActivityStartDate", ""),
            "analyte": row.get("CharacteristicName", ""),
            "fraction": row.get("ResultSampleFractionText", ""),
            "method": row.get("ResultAnalyticalMethod/MethodIdentifier", ""),
            **parsed,
            "status": status,
            "status_detail": detail,
            "flags": ";".join(flags),
            "analysis_eligible": status == "eligible",
        }
        # an observation is only defined for rows that may enter the analysis
        record["observation"] = (
            (record["limit_value"] if record["censored"] else record["value"])
            if record["analysis_eligible"] else None)
        canonical.append(record)
        counts[status] = counts.get(status, 0) + 1
        if record["analysis_eligible"]:
            groups[record["analysis_group"]] = groups.get(record["analysis_group"], 0) + 1

    return canonical, {
        "rows_in": len(rows),
        "rows_out": len(canonical),
        "status_counts": dict(sorted(counts.items())),
        "analysis_rows": counts.get("eligible", 0),
        "censored_rows": sum(1 for r in canonical if r["analysis_eligible"] and r["censored"]),
        "unresolved_rows": sum(v for k, v in counts.items()
                               if k.startswith(("ambiguous", "missing", "duplicate_conflicting",
                                                "conflicting", "nonfinite"))),
        "groups": dict(sorted(groups.items())),
    }

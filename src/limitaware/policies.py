"""Versioned interpretation policies.

A policy never changes the raw content; it decides interpretation and analysis
eligibility. Policies are plain JSON so that a transformation can be re-run exactly.
"""

from __future__ import annotations

import json
import math
import pathlib

POLICY_VERSION = "1.1"
SUPPORTED_VERSIONS = {"1.0", "1.1"}

DEFAULT_POLICY = {
    "policy_version": POLICY_VERSION,
    "name": "reporting-limit-total",
    "admissible_fractions": ["Total"],
    "admissible_methods": None,          # None = all methods
    "units": {
        "target": "ug/L",
        "conversions": {"ug/l": 1.0, "ug/L": 1.0, "ng/l": 0.001, "ng/L": 0.001},
    },
    "censoring_limit_roles": ["reporting"],
    "below_loq": "exclude",              # exclude | keep_as_detected
    "duplicates": "keep",                # keep | drop_identical
    "qc_activities": "exclude",          # exclude | keep
    "treat_missing_limit_for_detected": "allow",   # allow | require
    "estimated_results": "exclude",      # exclude | keep_as_detected
    "boundary_tolerance": 1e-9,          # relative tolerance for embedded vs inline bounds
}

BROAD_POLICY = {
    **DEFAULT_POLICY,
    "name": "any-limit-total",
    "censoring_limit_roles": ["reporting", "mdl", "loq", "other"],
}

VALID_ROLES = {"reporting", "mdl", "loq", "other", "unknown", ""}
VALID_CHOICES = {
    "below_loq": {"exclude", "keep_as_detected"},
    "duplicates": {"drop_identical", "keep"},
    "qc_activities": {"exclude", "keep"},
    "treat_missing_limit_for_detected": {"allow", "require"},
    "estimated_results": {"exclude", "keep_as_detected"},
}


class PolicyError(ValueError):
    pass


def validate(policy: dict) -> dict:
    if not isinstance(policy, dict):
        raise PolicyError("policy must be a JSON object")
    merged = dict(DEFAULT_POLICY)
    merged.update(policy)
    version = merged.get("policy_version", POLICY_VERSION)
    if version not in SUPPORTED_VERSIONS:
        raise PolicyError(f"unsupported policy_version {version!r}; "
                          f"supported: {sorted(SUPPORTED_VERSIONS)}")
    roles = merged.get("censoring_limit_roles")
    if not isinstance(roles, list) or not roles:
        raise PolicyError("censoring_limit_roles must be a non-empty list")
    bad = [r for r in roles if r not in VALID_ROLES]
    if bad:
        raise PolicyError(f"unknown limit roles: {bad}")
    for key, allowed in VALID_CHOICES.items():
        if merged[key] not in allowed:
            raise PolicyError(f"{key} must be one of {sorted(allowed)}")
    units = merged.get("units") or {}
    if not isinstance(units, dict) or "target" not in units or "conversions" not in units:
        raise PolicyError("units must define 'target' and 'conversions'")
    conversions = units["conversions"]
    if not isinstance(conversions, dict) or not conversions:
        raise PolicyError("units.conversions must be a non-empty object")
    for unit, factor in conversions.items():
        if not isinstance(unit, str) or not unit:
            raise PolicyError("unit names must be non-empty strings")
        if isinstance(factor, bool) or not isinstance(factor, (int, float)):
            raise PolicyError(f"conversion factor for {unit!r} must be a number")
        if not math.isfinite(float(factor)) or float(factor) <= 0:
            raise PolicyError(f"conversion factor for {unit!r} must be finite and > 0")
    if units["target"] not in conversions:
        raise PolicyError("units.target must appear in units.conversions")
    if float(conversions[units["target"]]) != 1.0:
        raise PolicyError("the target unit must have a conversion factor of exactly 1.0")
    tol = merged.get("boundary_tolerance", 1e-9)
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(float(tol)) or tol <= 0:
        raise PolicyError("boundary_tolerance must be a finite number > 0")
    if not isinstance(merged.get("admissible_methods"), (list, type(None))):
        raise PolicyError("admissible_methods must be a list or null")
    fractions = merged.get("admissible_fractions")
    if not isinstance(fractions, list) or not fractions:
        raise PolicyError("admissible_fractions must be a non-empty list")
    if not all(isinstance(f, str) and f for f in fractions):
        raise PolicyError("admissible_fractions must contain non-empty strings")
    return merged


def load(path: str | pathlib.Path) -> dict:
    try:
        payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyError(f"policy file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PolicyError(f"invalid policy JSON: {exc.msg}") from exc
    return validate(payload)


def save(policy: dict, path: str | pathlib.Path) -> None:
    pathlib.Path(path).write_text(json.dumps(validate(policy), indent=2), encoding="utf-8")

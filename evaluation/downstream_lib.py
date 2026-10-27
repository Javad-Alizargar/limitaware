"""Shared downstream schema and validation for LimitAware analyses."""
from __future__ import annotations
import json, math, pathlib

SCHEMA = json.loads((pathlib.Path(__file__).resolve().parent / "downstream_schema.json").read_text())
FIELDS = SCHEMA["fields"]; NUMERIC = set(SCHEMA["numeric"]); STATUS = set(SCHEMA["fit_status"])
MISSING = SCHEMA["missing"]

class MalformedOutput(ValueError): pass
class InvalidResult(ValueError): pass

def missing_row(export, policy, group, n, n_detected, n_censored, distinct, status, failure):
    row = {f: MISSING for f in FIELDS}
    row.update(export=export, policy=policy, group=group, n=str(n),
               n_detected=str(n_detected), n_censored=str(n_censored),
               distinct_censoring_limits=str(distinct), fit_status=status,
               warning=MISSING, failure_reason=failure)
    return row

def parse_r_output(text: str) -> dict:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) != 2:
        raise MalformedOutput(f"expected header + one row, got {len(lines)} non-empty lines")
    header = lines[0].split("\t")
    if header != FIELDS:
        raise MalformedOutput(f"header mismatch: {header}")
    values = lines[1].split("\t")
    if len(values) != len(FIELDS):
        raise MalformedOutput(f"field count {len(values)} != {len(FIELDS)}")
    row = dict(zip(FIELDS, values))
    return validate_row(row)

def validate_row(row: dict) -> dict:
    if set(row) != set(FIELDS):
        raise MalformedOutput("row fields do not match schema")
    if row["fit_status"] not in STATUS:
        raise MalformedOutput(f"invalid fit_status {row['fit_status']!r}")
    for f in NUMERIC:
        v = row[f]
        if v in (MISSING, "", None):
            continue
        try:
            x = float(v)
        except ValueError as e:
            raise MalformedOutput(f"non-numeric {f}: {v!r}") from e
        if not math.isfinite(x):
            raise InvalidResult(f"non-finite {f}: {v!r}")
    for f in ("n","n_detected","n_censored","distinct_censoring_limits"):
        if row[f] not in (MISSING, ""):
            if int(float(row[f])) < 0:
                raise InvalidResult(f"negative count {f}")
    return row

def write_tsv(path, rows):
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(validate_row(dict(r)))

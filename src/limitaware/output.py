"""Output writers: canonical table, raw sidecar, grouped analysis inputs, audit, note."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re

from . import __version__
from .contract import CONTRACT_NOTES, CONTRACT_VERSION, sha256

CANONICAL_FIELDS = [
    "source_row", "source_sha256", "result_uid",
    "organization", "activity_id", "activity_type", "activity_date",
    "analyte", "fraction", "method", "analysis_group",
    "condition_raw", "qualifier_raw", "qualifier_class", "embedded_qualifier",
    "interval_value", "value_raw", "value", "value_nonfinite",
    "unit_raw", "unit", "unit_factor",
    "censored", "limit_raw", "limit_value", "limit_nonfinite",
    "limit_unit_raw", "limit_factor", "limit_type_raw", "limit_role",
    "limit_source", "bound_conflict", "bound_delta", "observation",
    "status", "status_detail", "flags", "analysis_eligible",
]


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return ""
        return f"{value:.12g}"
    return value


def write_raw(rows: list[dict], header: list[str], digest: str, path: pathlib.Path) -> None:
    """Complete raw records, with the source digest, row number and derived uid."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header + ["source_row", "source_sha256", "result_uid"])
        for row in rows:
            writer.writerow([row.get(c, "") for c in header]
                            + [row["source_row"], digest, row["result_uid"]])


def write_canonical(rows: list[dict], path: pathlib.Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CANONICAL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.get(k)) for k in CANONICAL_FIELDS})


class OutputError(ValueError):
    """Raised when an output directory cannot be used safely."""


ARTEFACT_PREFIXES = ("analysis.",)
ARTEFACT_NAMES = {"canonical.csv", "raw_records.csv", "audit.json",
                  "methods_note.md", "analysis_manifest.json"}


def prepare_outdir(path: pathlib.Path, force: bool = False) -> None:
    """Create the output directory or clean only this tool's previous artefacts.

    Refuses a non-empty directory unless ``force`` is set; with ``force`` it removes
    only files this tool produces, so unrelated files are never deleted and stale
    group files cannot survive a rerun.
    """
    path = pathlib.Path(path)
    if not path.exists():
        path.mkdir(parents=True)
        return
    if not path.is_dir():
        raise OutputError(f"output path exists and is not a directory: {path}")
    entries = list(path.iterdir())
    if not entries:
        return
    if not force:
        raise OutputError(
            f"output directory is not empty: {path}. Rerun with --force to remove "
            "previous limitaware artefacts (unrelated files are kept).")
    for entry in entries:
        if entry.is_file() and (entry.name in ARTEFACT_NAMES
                                or entry.name.startswith(ARTEFACT_PREFIXES)):
            entry.unlink()


def _group_slug(group: str) -> str:
    """Collision-resistant file slug: readable part + hash of the structured key."""
    readable = re.sub(r"[^A-Za-z0-9._-]+", "_", group)[:60].strip("_") or "group"
    digest = hashlib.sha1(group.encode("utf-8")).hexdigest()[:8]
    return f"{readable}.{digest}"


def write_analysis(rows: list[dict], outdir: pathlib.Path) -> dict:
    """One analysis file per (fraction, method) group; never pooled.

    The tool refuses to emit a pooled file: methods and fractions differ in
    meaning, so each group gets its own file and a manifest.
    """
    groups: dict[str, list[dict]] = {}
    for row in rows:
        if row["analysis_eligible"]:
            groups.setdefault(row["analysis_group"], []).append(row)
    manifest = {"generated_by": f"limitaware {__version__}", "groups": {}}
    for group, members in sorted(groups.items()):
        name = f"analysis.{_group_slug(group)}.csv"
        with (outdir / name).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["obs", "censored", "result_uid", "source_row",
                             "source_sha256", "activity_id", "analyte", "fraction",
                             "method", "limit_role", "limit_source", "unit"])
            for row in members:
                writer.writerow([_fmt(row["observation"]),
                                 "TRUE" if row["censored"] else "FALSE",
                                 row["result_uid"], row["source_row"],
                                 row.get("source_sha256", ""), row["activity_id"],
                                 row["analyte"], row["fraction"], row["method"],
                                 row["limit_role"], row["limit_source"], row["unit"]])
        manifest["groups"][group] = {
            "file": name, "rows": len(members),
            "censored": sum(1 for r in members if r["censored"]),
        }
    (outdir / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2),
                                                    encoding="utf-8")
    # convenience copy only when a single group exists (never a pooled file)
    if len(groups) == 1:
        only = next(iter(manifest["groups"].values()))["file"]
        (outdir / "analysis.csv").write_bytes((outdir / only).read_bytes())
    return manifest


def build_audit(input_path: pathlib.Path, contract: dict, policy: dict,
                summary: dict, limits_report: dict) -> dict:
    return {
        "package": "limitaware",
        "package_version": __version__,
        "contract_version": CONTRACT_VERSION,
        "input": input_path.name,
        "input_sha256": sha256(input_path),
        "input_bytes": input_path.stat().st_size,
        "sidecars": {"raw_records": "raw_records.csv", "canonical": "canonical.csv",
                     "analysis_manifest": "analysis_manifest.json"},
        "contract": contract,
        "policy": policy,
        "limits_export": limits_report,
        "summary": summary,
        "rules": {
            "layers": ["raw", "parsed", "eligibility", "policy-dependent censoring"],
            "censoring": ("left-censored when the condition is 'Not Detected', the value "
                          "carries '<', or the qualifier is < / LT / U / ND; the "
                          "threshold is the reported or embedded limit, converted"),
            "right_and_interval": ("'<'/'LT'/'U'/'ND' are left-censored; '>' and interval "
                                   "values are rejected from left-censored exports"),
            "limit_roles": "MDL, reporting limit and LOQ are distinct and never pooled",
            "below_loq": ("'Present Below Quantification Limit' keeps the reported value "
                          "only under keep_as_detected; otherwise excluded"),
            "estimated": "J/R/unknown qualifiers never become exact detections",
            "bounds": ("an embedded bound and an inline limit must agree within the "
                       "policy tolerance in the target unit; otherwise conflicting_bound"),
            "duplicates": ("default keep; exact duplicates are only dropped under "
                           "drop_identical and a full identity key including organisation, "
                           "units and raw qualifier/condition"),
            "groups": "analysis inputs are written per (fraction, method); never pooled",
            "unresolved": "ambiguous or missing metadata keeps the row with a status",
        },
        "contract_notes": CONTRACT_NOTES,
    }


def write_audit(audit: dict, path: pathlib.Path) -> None:
    path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")


def write_methods_note(audit: dict, summary: dict, manifest: dict, path: pathlib.Path) -> None:
    s = summary
    p = audit["policy"]
    lines = [
        "# Methods note (generated)",
        "",
        f"Input: `{audit['input']}` (SHA-256 `{audit['input_sha256'][:16]}…`, "
        f"{audit['input_bytes']} bytes).",
        f"Contract: `{audit['contract_version']}`. Package: limitaware "
        f"{audit['package_version']}.",
        "",
        "## Interpretation policy",
        "",
        f"- Policy: `{p['name']}` (version {p['policy_version']}).",
        f"- Admissible fractions: {p['admissible_fractions']}.",
        f"- Admissible methods: {p['admissible_methods'] or 'all'}.",
        f"- Target unit: {p['units']['target']}; conversions: {p['units']['conversions']}.",
        f"- Limit roles admissible as censoring thresholds: {p['censoring_limit_roles']}.",
        f"- Below-LOQ results: {p['below_loq']}; estimated results: {p['estimated_results']}.",
        f"- Duplicate handling: {p['duplicates']}.",
        f"- QC activities: {p['qc_activities']}.",
        f"- Bound tolerance (relative): {p['boundary_tolerance']}.",
        "",
        "## Outcome",
        "",
        f"- Source rows: {s['rows_in']}; output rows: {s['rows_out']} "
        f"(one per source row).",
        f"- Analysis-eligible: {s['analysis_rows']} (censored {s['censored_rows']}).",
        f"- Unresolved (ambiguous, conflicting or non-finite): {s['unresolved_rows']}.",
        "",
        "| Status | Rows |",
        "| --- | --- |",
    ]
    for status, count in s["status_counts"].items():
        lines.append(f"| `{status}` | {count} |")
    lines += ["", "## Analysis groups (written separately, never pooled)", "",
              "| Group | Rows | Censored | File |", "| --- | --- | --- | --- |"]
    for group, info in manifest.get("groups", {}).items():
        lines.append(f"| `{group}` | {info['rows']} | {info['censored']} | `{info['file']}` |")
    lines += [
        "",
        "## Interpretation rules applied",
        "",
        "- Censoring is a property of the reported result; the threshold is the "
        "reported or embedded limit converted to the target unit.",
        "- Right-censored (`>`) and interval-censored values are rejected from "
        "left-censored exports and keep their source text.",
        "- Estimated (`J`), rejected (`R`) and unknown qualifiers never become exact "
        "detections.",
        "- An embedded bound and an inline limit must agree within tolerance; "
        "conflicts are unresolved, not silently resolved.",
        "- Duplicates are preserved by default; dropping requires an exact full-identity "
        "match under an explicit policy.",
        "- Fractions and methods are never pooled: each group has its own file.",
        "",
        "These rules describe what was done to this file. They do not establish that "
        "any resulting estimate is scientifically preferred to another policy.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")

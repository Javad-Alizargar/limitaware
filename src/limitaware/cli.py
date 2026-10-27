"""Command line interface: inspect, validate, transform, compare-policies."""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

from . import __version__, canonical, contract, output, policies


def _load(path, policy_path=None, expect_sha256=None):
    if expect_sha256:
        contract.verify_hash(path, expect_sha256)
    rows, header = contract.read_rows(path)
    report = contract.check_columns(header)
    if not report["ok"]:
        raise SystemExit(f"missing required columns: {report['missing']}")
    policy = policies.load(policy_path) if policy_path else policies.validate(dict(policies.DEFAULT_POLICY))
    return rows, header, report, policy


def cmd_inspect(args) -> int:
    rows, header, report, _ = _load(args.input)
    from collections import Counter
    def dist(col):
        return dict(Counter((r.get(col) or "").strip() for r in rows).most_common(8))
    payload = {
        "contract": report,
        "rows": len(rows),
        "columns": len(header),
        "activity_type": dist("ActivityTypeCode"),
        "fraction": dist("ResultSampleFractionText"),
        "units": dist("ResultMeasure/MeasureUnitCode"),
        "condition": dist("ResultDetectionConditionText"),
        "limit_type": dist("DetectionQuantitationLimitTypeName"),
        "limit_value": dist("DetectionQuantitationLimitMeasure/MeasureValue"),
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_validate(args) -> int:
    rows, header, report, policy = _load(args.input, args.policy, args.expect_sha256)
    print(json.dumps({"contract": report, "policy": policy["name"],
                      "rows": len(rows), "policy_valid": True}, indent=2))
    return 0


def _run_transform(input_path, policy, outdir: pathlib.Path, limits_path=None,
                   force: bool = False):
    rows, header = contract.read_rows(input_path)
    report = contract.check_columns(header)
    if not report["ok"]:
        raise SystemExit(f"missing required columns: {report['missing']}")
    limits_rows = None
    if limits_path:
        limits_rows, _ = contract.read_rows(limits_path)
    limits_report = canonical.link_limits(rows, limits_rows)
    records, summary = canonical.transform(rows, policy)

    output.prepare_outdir(outdir, force=force)
    digest = contract.sha256(pathlib.Path(input_path))
    for record, raw in zip(records, rows):
        record["source_sha256"] = digest
        raw["result_uid"] = record["result_uid"]
    output.write_raw(rows, header, digest, outdir / "raw_records.csv")
    output.write_canonical(records, outdir / "canonical.csv")
    manifest = output.write_analysis(records, outdir)
    audit = output.build_audit(pathlib.Path(input_path), report, policy, summary, limits_report)
    output.write_audit(audit, outdir / "audit.json")
    output.write_methods_note(audit, summary, manifest, outdir / "methods_note.md")
    return records, summary, audit


def cmd_transform(args) -> int:
    if args.expect_sha256:
        contract.verify_hash(args.input, args.expect_sha256)
    records, summary, audit = _run_transform(
        args.input, policies.load(args.policy),
        pathlib.Path(args.out), args.limits, args.force)
    print(json.dumps({"summary": summary,
                      "policy": audit["policy"]["name"],
                      "out": str(args.out)}, indent=2))
    return 0


def cmd_compare(args) -> int:
    outdir = pathlib.Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    paths = [p.strip() for p in args.policies.split(",") if p.strip()]
    rows_out = []
    for path in paths:
        policy = policies.load(path)
        sub = outdir / policy["name"]
        _, summary, _ = _run_transform(args.input, policy, sub, force=args.force)
        rows_out.append({"policy": policy["name"], **summary})
    with (outdir / "policy_comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        writer.writeheader(); writer.writerows(rows_out)
    print(json.dumps(rows_out, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="limitaware",
                                 description="WQP result preparation with explicit "
                                             "interpretation policies.")
    ap.add_argument("--version", action="version", version=f"limitaware {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect", help="summarise an export")
    p.add_argument("input"); p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("validate", help="check contract and policy")
    p.add_argument("input"); p.add_argument("--policy", required=True)
    p.add_argument("--expect-sha256", default=None)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("transform", help="produce canonical, analysis and audit outputs")
    p.add_argument("input"); p.add_argument("--policy", required=True)
    p.add_argument("--out", required=True); p.add_argument("--limits", default=None)
    p.add_argument("--expect-sha256", default=None)
    p.add_argument("--force", action="store_true",
                   help="remove previous limitaware artefacts in the output directory")
    p.set_defaults(func=cmd_transform)

    p = sub.add_parser("compare-policies", help="transform under several policies")
    p.add_argument("input"); p.add_argument("--policies", required=True)
    p.add_argument("--out", required=True); p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_compare)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (policies.PolicyError, contract.ContractError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

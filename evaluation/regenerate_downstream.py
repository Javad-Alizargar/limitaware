#!/usr/bin/env python3
"""Regenerate the downstream table with the validated 15-field schema."""
from __future__ import annotations
import csv, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evaluation"))
from downstream_lib import FIELDS, MISSING, MalformedOutput, InvalidResult, missing_row, parse_r_output, validate_row, write_tsv

POL = ROOT / "evaluation/expanded/policy_results"
OUT = ROOT / "evaluation/expanded/downstream.tsv"
OLD = ROOT / "evaluation/expanded/downstream_superseded_2026-10-26.tsv"

def screen(data):
    n = len(data)
    ndet = sum(1 for x in data if x["censored"] != "TRUE")
    ncen = n - ndet
    lim = {round(float(x["obs"]), 12) for x in data if x["censored"] == "TRUE"}
    if ndet < 8:
        return missing_row("", "", "", n, ndet, ncen, len(lim), "skipped_insufficient_detects", "n_detected<8")
    if ncen < 1:
        return missing_row("", "", "", n, ndet, ncen, len(lim), "skipped_no_censoring", "n_censored<1")
    if not lim:
        return missing_row("", "", "", n, ndet, ncen, 0, "skipped_no_limit", "no distinct limit")
    return None

def main():
    if OUT.exists() and not OLD.exists():
        OLD.write_bytes(OUT.read_bytes())
    rows = []
    for export_dir in sorted(p for p in POL.iterdir() if p.is_dir()):
        for poldir in sorted(export_dir.glob("P*")):
            man = json.loads((poldir / "analysis_manifest.json").read_text())
            for group, meta in man["groups"].items():
                data = list(csv.DictReader(open(poldir / meta["file"])))
                skip = screen(data)
                if skip:
                    skip.update(export=export_dir.name, policy=poldir.name, group=group)
                    rows.append(validate_row(skip)); continue
                cp = subprocess.run(["Rscript", str(ROOT/"evaluation/scripts/nada_group_summary.R"),
                                     str(poldir/meta["file"]), export_dir.name, poldir.name, group],
                                    capture_output=True, text=True)
                if cp.returncode:
                    rows.append(validate_row(missing_row(export_dir.name, poldir.name, group,
                        len(data), sum(1 for x in data if x["censored"]!="TRUE"),
                        sum(1 for x in data if x["censored"]=="TRUE"),
                        len({x["obs"] for x in data if x["censored"]=="TRUE"}),
                        "r_error", cp.stderr.strip().replace("\n"," ")[:200])))
                    continue
                try:
                    rows.append(parse_r_output(cp.stdout))
                except (MalformedOutput, InvalidResult) as e:
                    rows.append(validate_row(missing_row(export_dir.name, poldir.name, group,
                        len(data), 0, 0, 0, "malformed_output", str(e))))
    write_tsv(OUT, rows)
    (ROOT/"evaluation/expanded/downstream.json").write_text(json.dumps(rows, indent=2))
    # compare fitted values with the superseded table by key
    old = {}
    if OLD.exists():
        for r in csv.DictReader(open(OLD), delimiter="\t"):
            if r.get("status") == "ok":
                old[(r["export"], r["policy"], r["group"])] = r
    diffs = []
    for r in rows:
        if r["fit_status"] not in ("ok","ok_median_not_identified"): continue
        o = old.get((r["export"], r["policy"], r["group"]))
        if not o: continue
        for a,b in (("mean","mean"),("mean_lcl","mean_lcl"),("mean_ucl","mean_ucl")):
            if r[a] not in ("NA","") and o.get(b):
                diffs.append(abs(float(r[a]) - float(o[b])))
    print(json.dumps({"rows":len(rows),"fits":sum(1 for r in rows if r["fit_status"].startswith("ok")),
        "skipped":sum(1 for r in rows if r["fit_status"].startswith("skipped")),
        "errors":sum(1 for r in rows if r["fit_status"] in ("r_error","invalid_nonfinite","malformed_output")),
        "max_abs_difference_vs_superseded":max(diffs) if diffs else None,
        "fields":FIELDS}, indent=2))
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Replay a development export from its archived raw-record sidecar.

The sidecar preserves every delivered field but not the original CSV bytes (the
download hash cannot be reconstructed). Usage:
  python evaluation/replay_from_sidecar.py EXPORT WORKDIR
where EXPORT is iowa, NY or OH.
"""
import csv, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / "packages/limitaware" if (ROOT / "packages/limitaware").exists() else ROOT
SRC = {"iowa": ROOT/"evaluation/results_0.1.4/iowa/limitaware/raw_records.csv",
       "NY": ROOT/"evaluation/results_0.1.4/NY/limitaware/raw_records.csv",
       "OH": ROOT/"evaluation/results_0.1.4/OH/limitaware/raw_records.csv"}
POL = {"iowa":"reporting_total", "NY":"reporting_dissolved", "OH":"reporting_dissolved"}
GEN = {"source_row","source_sha256","result_uid"}
def main(export, work):
    work = pathlib.Path(work); work.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(SRC[export], newline="", encoding="utf-8", errors="replace")))
    fields = [k for k in rows[0].keys() if k not in GEN]
    rebuilt = work/f"{export}_from_sidecar.csv"
    with rebuilt.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    out = work/f"{export}_replay"
    subprocess.run([sys.executable,"-m","limitaware.cli","transform",str(rebuilt),"--policy",
                    str(PKG/f"policies/{POL[export]}.json"),"--out",str(out),"--force"], check=True)
    new = json.loads((out/"audit.json").read_text())["summary"]
    old = json.loads((ROOT/f"evaluation/results_0.1.4/{export}/limitaware/audit.json").read_text())["summary"]
    same = new["status_counts"] == old["status_counts"]
    print(json.dumps({"export":export,"rows":new["rows_in"],
        "status_counts_equal":same,"reconstructed_sha256":__import__("hashlib").sha256(rebuilt.read_bytes()).hexdigest()[:16],
        "original_input_sha256":json.loads((ROOT/f"evaluation/results_0.1.4/{export}/limitaware/audit.json").read_text())["input_sha256"][:16],
        "note":"reconstructed bytes do not match the original download hash"}, indent=2))
    assert same
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

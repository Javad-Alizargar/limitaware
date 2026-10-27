#!/usr/bin/env python3
"""Software-only verification promised by the public package.

Does not need the held-out study bundle. Checks installation, policies, the
documented fixture contract and the package tests.
"""
from __future__ import annotations
import json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / "packages/limitaware" if (ROOT / "packages/limitaware").exists() else ROOT
if str(PKG / "src") not in sys.path:
    sys.path.insert(0, str(PKG / "src"))
import limitaware
from limitaware import canonical, contract, policies

def main():
    print("version:", limitaware.__version__)
    assert limitaware.__version__ == "0.1.4"
    for p in sorted((PKG / "policies").glob("*.json")):
        policies.load(str(p))
    fixture = PKG / "tests/fixtures/interpretation_cases.csv"
    rows, header = contract.read_rows(fixture)
    report = contract.check_columns(header); assert report["ok"]
    policy = policies.load(str(PKG / "policies/reporting_total.json"))
    records, summary = canonical.transform(rows, policy)
    expected = json.loads((PKG / "tests/fixtures/expected.json").read_text())
    got = {r["case_id"]: rec["status"] for r, rec in zip(rows, records)}
    assert all(got[k] == v["status"] for k, v in expected.items()), got
    cp = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                        cwd=PKG, capture_output=True, text=True,
                        env={**__import__("os").environ, "PYTHONPATH": str(PKG/"src")})
    if cp.returncode:
        print(cp.stdout[-1200:]); print(cp.stderr[-1200:]); raise SystemExit("package tests failed")
    print("fixtures:", summary["status_counts"])
    print("software-only verification passed (study replay not executed)")

if __name__ == "__main__": main()

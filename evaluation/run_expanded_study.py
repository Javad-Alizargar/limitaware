#!/usr/bin/env python3
"""Restartable analytical replay for the expanded LimitAware study.

Recomputes agreement, policy transitions and downstream summaries from archived
held-out inputs. Historical acquisition is separate; no stored JSON is copied.

Usage:
  python evaluation/run_expanded_study.py --stage all --workdir /tmp/la_replay
  python evaluation/run_expanded_study.py --stage verify
"""
from __future__ import annotations
import argparse, csv, hashlib, json, pathlib, shutil, subprocess, sys
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from downstream_lib import FIELDS, MalformedOutput, InvalidResult, missing_row, parse_r_output, validate_row, write_tsv

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / "packages/limitaware" if (ROOT / "packages/limitaware").exists() else ROOT
EVAL = ROOT / "evaluation"; EXP = EVAL / "expanded"; RESULTS = EXP / "results_0.1.4"
EXPORTS = {
 "illinois": (EXP/"data/illinois_atrazine_2022.csv", "reporting_total"),
 "indiana": (EXP/"data/indiana_metolachlor_2022.csv", "reporting_total"),
 "minnesota": (EXP/"data/minnesota_24_d_2022.csv", "reporting_total"),
 "wisconsin": (EXP/"data/wisconsin_metolachlor_2022.csv", "reporting_total"),
 "mississippi": (EXP/"data/mississippi_atrazine_2022.csv", "reporting_dissolved"),
}
CFG = {"reporting_total":"baseline_total.json", "reporting_dissolved":"baseline_dissolved.json"}
ORDER = ["unsupported_interval_censored","unsupported_right_censored","ambiguous_qualifier",
 "conflicting_qualifier","excluded_rejected","excluded_estimated","excluded_qc","excluded_fraction",
 "excluded_method","excluded_value_type","unsupported_unit","nonfinite_value","nonfinite_limit",
 "conflicting_bound","duplicate_identical","ambiguous_condition","missing_limit",
 "unsupported_limit_unit","excluded_limit_role","eligible","excluded_below_loq","ambiguous_missing_value"]
FLAG = {"excluded_value_type":"value_type_not_actual","excluded_qc":("qc_activity","field_measurement"),
 "excluded_fraction":"fraction_not_admissible","excluded_limit_role":"limit_role_not_admissible",
 "excluded_below_loq":"below_loq","excluded_estimated":"estimated_result","unsupported_unit":"unit_unconvertible",
 "missing_limit":"limit_missing","ambiguous_qualifier":"qualifier_unknown",
 "unsupported_right_censored":"right_censored","excluded_method":"method_not_admissible"}

def sha16(p): return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
def run(cmd):
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode: raise SystemExit(f"failed: {' '.join(cmd)}\n{cp.stderr[-1500:]}")
    return cp

def verify():
    req = json.loads((EVAL / "STUDY_REPRODUCTION_REQUIREMENTS.json").read_text())
    missing = [(x["path"], x["role"]) for x in req["files"] if not (ROOT / x["path"]).exists()]
    if missing:
        print("study bundle incomplete; missing", len(missing), "required files:")
        for path, role in missing:
            print(f"  - {path} ({role})")
        print("Use evaluation/verify_software.py for software-only checks, or supply the")
        print("bundle described in evaluation/STUDY_REPRODUCTION_REQUIREMENTS.json.")
        raise SystemExit(2)
    for x in req["files"]:
        f = ROOT / x["path"]
        assert sha16(f) == x["sha256"][:16], f"digest mismatch: {x['path']}"
    expected = (EVAL/"EXPANDED_PROTOCOL.sha256").read_text().split()[0]
    got = hashlib.sha256((EVAL/"EXPANDED_PROTOCOL.md").read_bytes()).hexdigest()
    assert got == expected, "protocol hash mismatch"
    print("verify: study bundle present; all required files and protocol hash match")

def policy(base, variant):
    return str(PKG/f"policies/{base}.json") if variant=="P0" else str(EXP/f"policies/{base}_{variant}.json")

def prepare(work):
    for n,(f,base) in EXPORTS.items():
        for v in ("P0","P1","P2","P3","P4","P5"):
            run([sys.executable,"-m","limitaware.cli","transform",str(f),"--policy",policy(base,v),"--out",str(work/"prepare"/n/v),"--force"])
    print("prepare: five exports x six policies")

def baseline(work):
    for n,(f,base) in EXPORTS.items():
        run([sys.executable,str(EVAL/"scripts/baseline_prepare.py"),str(f),str(work/"baseline"/n),str(EVAL/"configs"/CFG[base])])
    print("baseline: five matched runs")

def classify(la, bs):
    if la["status"]==bs: return "same"
    if la["status"]=="eligible" or bs=="eligible": return "substantive"
    key=FLAG.get(bs); present=False
    if key:
        keys=key if isinstance(key,tuple) else (key,)
        present=any(x.split(":")[0] in keys for x in la["flags"].split(";") if x)
    return "precedence" if present and ORDER.index(la["status"])<ORDER.index(bs) else "substantive"

def compare(work):
    out=[]
    for n in EXPORTS:
        la={r["source_row"]:r for r in csv.DictReader(open(work/"prepare"/n/"P0/canonical.csv"))}
        bl={r["row"]:r for r in csv.DictReader(open(work/"baseline"/n/"prepared.csv"))}
        nrows = sum(1 for _ in csv.DictReader(open(EXPORTS[n][0], newline="", encoding="utf-8", errors="replace")))
        expected_rows = {str(i) for i in range(2, nrows + 2)}
        assert set(la) == expected_rows, f"canonical rows do not reconcile for {n}"
        assert len(bl) == nrows, f"baseline rows do not reconcile for {n}"
        le={k for k,r in la.items() if r["analysis_eligible"]=="true"}
        be={k for k,r in bl.items() if r["status"]=="eligible"}
        maxd=0.0; om=cm=gm=0
        for k in le & be:
            d=abs(float(la[k]["observation"])-float(bl[k]["obs"])); maxd=max(maxd,d); om+=d>1e-9
            cm+=(la[k]["censored"]=="true")!=(bl[k]["censored"]=="True")
            g=json.loads(la[k]["analysis_group"])
            gm+=(g["analyte"],g["fraction"],g["method"])!=(bl[k]["analyte"],bl[k]["fraction"],bl[k]["method"])
        pairs=Counter(); prec=0; subst=[]
        for k,r in la.items():
            if k not in bl: continue
            c=classify(r,bl[k]["status"])
            if c=="same": continue
            pairs[(bl[k]["status"],r["status"])]+=1
            (subst.append(k) if c=="substantive" else None)
            if c=="precedence": prec+=1
        out.append({"export":n,"rows":len(la),"eligible_limitaware":len(le),"eligible_baseline":len(be),
          "eligible_sets_identical":le==be,"eligible_intersection":len(le&be),"only_limitaware":len(le-be),
          "only_baseline":len(be-le),"max_abs_observation_difference":maxd,"observation_mismatches_gt_1e-9":om,
          "censoring_mismatches":cm,"group_mismatches":gm,
          "status_difference_pairs":{f"{a} -> {b}":v for (a,b),v in pairs.items()},
          "status_differences_total":sum(pairs.values()),"precedence_differences":prec,
          "substantive_differences":len(subst)})
    (work/"agreement.json").write_text(json.dumps({"exports":out},indent=2))
    ship={r["export"]:r for r in json.loads((RESULTS/"agreement.json").read_text())["exports"]}
    for r in out:
        s=ship[r["export"]]
        assert r["eligible_limitaware"]==s["eligible_limitaware"] and r["eligible_sets_identical"]==s["eligible_sets_identical"]
        assert r["status_differences_total"]==s["status_differences_total"] and r["precedence_differences"]==s["precedence_differences"]
        assert abs(r["max_abs_observation_difference"]-s["max_abs_observation_difference"])<1e-12
        assert r["observation_mismatches_gt_1e-9"]==s["observation_mismatches_gt_1e-9"]==0
        assert r["censoring_mismatches"]==s["censoring_mismatches"]==0
        assert r["group_mismatches"]==s["group_mismatches"]==0
    print("compare: eligible sets and status-difference counts reproduce shipped results")

def transitions(work):
    summary={}
    for n,(_,base) in EXPORTS.items():
        rec={}
        for v in ("P0","P1","P2","P3","P4","P5"):
            a=json.loads((work/"prepare"/n/v/"audit.json").read_text())["summary"]
            rec[v]={"status_counts":a["status_counts"],"eligible":a["analysis_rows"],"censored":a["censored_rows"],
                    "unresolved":a["unresolved_rows"],"groups":len(a["groups"])}
        p0={r["source_row"]:r for r in csv.DictReader(open(work/"prepare"/n/"P0/canonical.csv"))}
        trans={}
        for v in ("P1","P2","P3","P4","P5"):
            cur={r["source_row"]:r for r in csv.DictReader(open(work/"prepare"/n/v/"canonical.csv"))}
            c=Counter(); reasons=Counter()
            for k,r in p0.items():
                e0=r["analysis_eligible"]=="true"; e1=cur[k]["analysis_eligible"]=="true"; c[(e0,e1)]+=1
                if e0!=e1: reasons[f"{r['status']} -> {cur[k]['status']}"]+=1
            trans[v]={"eligible_to_eligible":c[(True,True)],"eligible_to_not":c[(True,False)],
                      "not_to_eligible":c[(False,True)],"not_to_not":c[(False,False)],"reasons":dict(reasons)}
        rec["transitions"]=trans; summary[n]={"base_policy":base,"variants":rec}
    (work/"policy_summary.json").write_text(json.dumps(summary,indent=2))
    ship=json.loads((EXP/"policy_results/policy_summary.json").read_text())
    for n in summary:
        for v in ("P0","P1","P2","P3","P4","P5"):
            a=summary[n]["variants"][v]; b=ship[n]["variants"][v]
            assert a["eligible"]==b["eligible"] and a["censored"]==b["censored"] and a["unresolved"]==b["unresolved"]
        for v in ("P1","P2","P3","P4","P5"):
            assert summary[n]["variants"]["transitions"][v]==ship[n]["variants"]["transitions"][v], (n,v)
    print("transitions: eligible/censored/unresolved counts and every row-level transition reproduce shipped results")

def downstream(work):
    if shutil.which("Rscript") is None:
        raise SystemExit("Rscript not found: full replay requires R/NADA. "
                         "Use --python-only for an explicitly limited replay.")
    canonical={(r["export"],r["policy"],r["group"]):r for r in csv.DictReader(open(EXP/"downstream.tsv"),delimiter="\t")}
    rows=[]
    for n in EXPORTS:
        for v in ("P0","P1","P2","P3","P4","P5"):
            d=work/"prepare"/n/v; man=json.loads((d/"analysis_manifest.json").read_text())
            for key,meta in man["groups"].items():
                data=list(csv.DictReader(open(d/meta["file"])))
                nrec=len(data); ndet=sum(1 for x in data if x["censored"]!="TRUE")
                ncen=nrec-ndet; lim={round(float(x["obs"]),12) for x in data if x["censored"]=="TRUE"}
                if ndet<8:
                    rows.append(validate_row(missing_row(n,v,key,nrec,ndet,ncen,len(lim),"skipped_insufficient_detects","n_detected<8"))); continue
                if ncen<1:
                    rows.append(validate_row(missing_row(n,v,key,nrec,ndet,ncen,len(lim),"skipped_no_censoring","n_censored<1"))); continue
                if not lim:
                    rows.append(validate_row(missing_row(n,v,key,nrec,ndet,ncen,0,"skipped_no_limit","no distinct limit"))); continue
                cp=subprocess.run(["Rscript",str(EVAL/"scripts/nada_group_summary.R"),str(d/meta["file"]),n,v,key],
                                  capture_output=True,text=True)
                if cp.returncode:
                    rows.append(validate_row(missing_row(n,v,key,nrec,ndet,ncen,len(lim),"r_error",cp.stderr.strip().replace("\n"," ")[:200]))); continue
                try:
                    rows.append(parse_r_output(cp.stdout))
                except (MalformedOutput, InvalidResult) as e:
                    rows.append(validate_row(missing_row(n,v,key,nrec,ndet,ncen,len(lim),"malformed_output",str(e))))
    write_tsv(work/"downstream.tsv", rows)
    (work/"downstream.json").write_text(json.dumps(rows,indent=2))
    bad=[r for r in rows if r["fit_status"] in ("r_error","invalid_nonfinite","malformed_output")]
    if bad: raise SystemExit(f"downstream failures: {len(bad)} rows")
    compared=0
    for r in rows:
        c=canonical.get((r["export"],r["policy"],r["group"]))
        if not c: raise SystemExit(f"canonical row missing for {r['export']} {r['policy']} {r['group']}")
        for f in ("n","n_detected","n_censored","distinct_censoring_limits","fit_status"):
            assert r[f]==c[f], (r["export"],r["policy"],r["group"],f,r[f],c[f])
        if r["fit_status"].startswith("ok"):
            for f in ("mean","mean_lcl","mean_ucl"):
                if c[f] not in ("NA","") and r[f] not in ("NA",""):
                    assert abs(float(r[f])-float(c[f]))<=1e-6*max(1,abs(float(c[f]))), (f,r[f],c[f])
            compared+=1
    print(f"downstream: {len(rows)} rows validate; {compared} fitted rows reproduce canonical means/CIs and all fit statuses/skips")

def tables(work):
    cov={}
    for n in EXPORTS:
        a=json.loads((work/"prepare"/n/"P0/audit.json").read_text())["summary"]
        cov[n]={"rows":a["rows_in"],"eligible":a["analysis_rows"],"unresolved":a["unresolved_rows"],"status_counts":a["status_counts"]}
    (work/"coverage.json").write_text(json.dumps(cov,indent=2))
    with (work/"table3.csv").open("w",newline="") as fh:
        w=csv.writer(fh); w.writerow(["export","P0","P1","P2","P3","P4","P5"])
        ps=json.loads((work/"policy_summary.json").read_text())
        for n in EXPORTS: w.writerow([n]+[ps[n]["variants"][v]["eligible"] for v in ("P0","P1","P2","P3","P4","P5")])
    print("tables: coverage and policy tables written")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",default="all",
        choices=["verify","prepare","baseline","compare","transitions","downstream","tables","all"])
    ap.add_argument("--workdir",default="/tmp/la_replay")
    ap.add_argument("--python-only", action="store_true",
                    help="skip R/NADA downstream stage; full replay is not claimed")
    a=ap.parse_args()
    work=pathlib.Path(a.workdir); work.mkdir(parents=True,exist_ok=True)
    order=["verify","prepare","baseline","compare","transitions","downstream","tables"]
    todo=order if a.stage=="all" else [a.stage]
    for s in todo:
        print("==",s,"==")
        if s=="verify":
            verify(); continue
        if s=="downstream" and a.python_only:
            (work/"downstream_scope.json").write_text(json.dumps({
                "scope":"python-only replay: R/NADA downstream stage skipped",
                "fit_checks":"not executed"}, indent=2))
            print("downstream: SKIPPED (python-only scope; no fit verification)")
            continue
        {"prepare":prepare,"baseline":baseline,"compare":compare,"transitions":transitions,
         "downstream":downstream,"tables":tables}[s](work)
    if a.python_only:
        print("python-only replay complete:",work,"— downstream R/NADA fit checks NOT executed")
    elif a.stage == "all":
        print("full replay complete:",work)
    else:
        print("stages complete:",", ".join(todo),"(",work,") — not a full replay")

if __name__=="__main__":
    main()

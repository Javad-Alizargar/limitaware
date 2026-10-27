#!/usr/bin/env python3
"""Regenerate the DL semantic audit from source records and canonical outputs."""
import csv, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SOURCES = {
 "illinois": (ROOT/"evaluation/expanded/data/illinois_atrazine_2022.csv",
              ROOT/"evaluation/expanded/results_0.1.4/illinois/limitaware/canonical.csv"),
 "iowa": (pathlib.Path("/tmp/wqp_US3A19.csv"),
          ROOT/"evaluation/results_0.1.4/iowa/limitaware/canonical.csv"),
}
rows=[]
for export,(rawf,canf) in SOURCES.items():
    if rawf.exists():
        raw={str(i):r for i,r in enumerate(csv.DictReader(open(rawf,newline="",encoding="utf-8",errors="replace")),start=2)}
    else:
        side=ROOT/f"evaluation/results_0.1.4/{'iowa' if export=='iowa' else export}/limitaware/raw_records.csv"
        raw={r["source_row"]:{k:v for k,v in r.items() if k not in ("source_row","source_sha256","result_uid")}
             for r in csv.DictReader(open(side,newline="",encoding="utf-8",errors="replace"))}
    can={r["source_row"]:r for r in csv.DictReader(open(canf))}
    for k,r in raw.items():
        if r["MeasureQualifierCode"]!="DL": continue
        c=can[k]
        condition=(r["ResultDetectionConditionText"] or "").strip()
        limit=(r["DetectionQuantitationLimitMeasure/MeasureValue"] or "").strip()
        numeric=bool(limit)
        if numeric:
            bound="reporting-limit bound above likely MDL; looser/upward-biased threshold"
            ordering="ordering assumed from general guidance, not measured; censoring threshold above unavailable MDL"
            unresolved=""
        else:
            bound="no numeric threshold"
            ordering="unavailable"
            unresolved="threshold cannot be established from the record"
        rows.append({
          "export":export,"source_row":k,"condition_present":str(bool(condition)).lower(),
          "condition_text":condition,"qualifier":r["MeasureQualifierCode"],
          "qualifier_supports_nondetect":"true","numeric_limit":str(numeric).lower(),
          "limit_type":r["DetectionQuantitationLimitTypeName"],
          "limit_value":limit,"limit_unit":r["DetectionQuantitationLimitMeasure/MeasureUnitCode"],
          "limit_role":c["limit_role"],"status":c["status"],"eligible":c["analysis_eligible"],
          "bound_evidence":bound,"ordering_evidence":ordering,"unresolved":unresolved,
          "comment":r["ResultCommentText"]})
out=ROOT/"evaluation/expanded/semantic_audit.csv"
with open(out,"w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
from collections import Counter
summary={
 "DL_records":len(rows),
 "qualifier_supports_nondetect":sum(1 for r in rows if r["qualifier_supports_nondetect"]=="true"),
 "condition_present":sum(1 for r in rows if r["condition_present"]=="true"),
 "numeric_limit":sum(1 for r in rows if r["numeric_limit"]=="true"),
 "no_numeric_limit":sum(1 for r in rows if r["numeric_limit"]=="false"),
 "by_export":dict(Counter(r["export"] for r in rows)),
 "by_limit_type":dict(Counter(r["limit_type"] for r in rows if r["numeric_limit"]=="true")),
 "status":dict(Counter(r["status"] for r in rows)),
 "ordering_evidence":dict(Counter(r["ordering_evidence"] for r in rows)),
}
(ROOT/"evaluation/expanded/semantic_audit_summary.json").write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))

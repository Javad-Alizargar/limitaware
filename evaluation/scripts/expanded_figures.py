#!/usr/bin/env python3
"""Expanded-study figures A-E (vector + raster + panel source data).

A  documented semantics and refusals on three real records
B  held-out coverage after the contract repair, and the repair effect
C  policy consequences: limit-role inclusion and downstream means
D  matched-baseline agreement across eight exports
E  measured CLI runtime by workload

Reads saved results only; writes evaluation/figures/fig[A-E]*.{png,svg,pdf} and
evaluation/figures/expanded_data/*.csv.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = pathlib.Path(__file__).resolve().parent
EVAL = HERE.parent
OUT = EVAL / "figures"
DATA = OUT / "expanded_data"
OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

C_LA, C_BL, C_PRE, C_WARN = "#1b6ca8", "#c25e00", "#9aa7b4", "#8c2d04"
STATUS_COLOURS = {
    "eligible": C_LA,
    "excluded_fraction": "#9db7cc",
    "excluded_qc": "#8d99a8",
    "excluded_value_type": "#7a8f5a",
    "excluded_limit_role": C_BL,
    "excluded_estimated": "#5d4037",
    "refused": C_WARN,
}
PLT = {"font.size": 8, "font.family": "DejaVu Sans", "axes.titlesize": 8.4,
       "axes.labelsize": 8, "axes.spines.top": False, "axes.spines.right": False}


def save(fig, stem):
    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / f"{stem}.{ext}", dpi=300)
    plt.close(fig)


def panel_a():
    cards = [
        ("Illinois row 70",
         "Not Detected, DL qualifier\nno result value, result unit ug/L\nlimit 0.1, Minimum Reporting Level",
         "WQX: DL = not detected at/above MDL;\nMRL is a reporting limit",
         "eligible, censored at 0.1 ug/L", "#eaf1f8"),
        ("Iowa row 318",
         "DL qualifier, value 0.1 ug/L\nno condition, no limit",
         "WQX: non-detect, but no threshold\ncan be established from the record",
         "missing_limit (refused)", "#fdf0e3"),
        ("Wisconsin row 2",
         "Not Detected, blank value/unit\nlimit value \"Check with DATCP\"",
         "sentinel is not a number; the\nthreshold cannot be parsed",
         "missing_limit (refused)", "#fbe9e7"),
    ]
    rows = [{"card": c[0], "raw": c[1].replace("\n", " | "), "evidence": c[2].replace("\n", " "),
             "decision": c[3]} for c in cards]
    with (DATA / "panel_a_records.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with plt.rc_context(PLT):
        fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.35))
        for ax, (title, raw, ev, decision, colour) in zip(axes, cards):
            ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
            ax.add_patch(FancyBboxPatch((0.2, 0.4), 9.6, 9.2, boxstyle="round,pad=0.15",
                                        fc=colour, ec="#7d8fa3", lw=0.7))
            ax.text(5, 9.0, title, ha="center", fontsize=7.6, fontweight="bold")
            ax.text(5, 7.3, raw, ha="center", va="top", fontsize=6.3, linespacing=1.45)
            ax.text(5, 4.3, ev, ha="center", va="top", fontsize=6.2, color="#33465c",
                    linespacing=1.4)
            ax.text(5, 1.9, decision, ha="center", fontsize=7.0, fontweight="bold",
                    color=C_LA if decision.startswith("eligible") else C_WARN)
        fig.suptitle("A  Documented semantics resolve some records and make refusals explicit",
                     y=0.99, fontsize=8.8, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        save(fig, "figA_semantics")


def panel_b():
    cov = json.loads((EVAL / "expanded/results_0.1.4/coverage.json").read_text())
    order = ["illinois", "indiana", "minnesota", "wisconsin", "mississippi"]
    classes = ["eligible", "excluded_fraction", "excluded_qc", "excluded_value_type",
               "excluded_limit_role", "excluded_estimated"]
    comp = []
    for name in order:
        d = cov[name]; rows = d["rows"]; counts = d["post"]
        ref = sum(v for k, v in counts.items() if k not in classes)
        comp.append({"export": name, "rows": rows, **{k: counts.get(k, 0) for k in classes},
                     "refused": ref, "eligible_pct": 100 * counts.get("eligible", 0) / rows})
    with (DATA / "panel_b_coverage.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(comp[0])); w.writeheader(); w.writerows(comp)

    with plt.rc_context(PLT):
        fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.9, 3.2), gridspec_kw={"width_ratios": [1.45, 1]})
        left = [0] * len(order)
        for cls in classes + ["refused"]:
            vals = [100 * c[cls] / c["rows"] for c in comp]
            ax.barh(range(len(order)), vals, left=left, color=STATUS_COLOURS[cls],
                    label=cls.replace("excluded_", "").replace("_", " ") if cls != "refused" else "refused/unresolved")
            left = [a + b for a, b in zip(left, vals)]
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([o.replace("_", " ").title() for o in order], fontsize=7)
        ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("share of source rows (%)")
        for i, c in enumerate(comp):
            ax.text(101, i, f"n={c['rows']}; {c['eligible_pct']:.0f}% eligible", va="center", fontsize=6.0)
        ax.legend(fontsize=5.4, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.18))
        ax.set_title("B1  Post-repair applicability", fontsize=8)

        pre = [cov[o]["pre_eligible"] for o in order]
        post = [cov[o]["post_eligible"] for o in order]
        for i, (p, q) in enumerate(zip(pre, post)):
            ax2.plot([p, q], [i, i], color="#b9c3cf", lw=3, zorder=1)
            ax2.scatter([p], [i], color=C_PRE, s=28, zorder=2)
            ax2.scatter([q], [i], color=C_LA, s=28, zorder=3)
            if q != p:
                ax2.text(q + 8, i, f"+{q-p}", va="center", fontsize=6.0, color=C_LA)
        ax2.set_yticks(range(len(order))); ax2.set_yticklabels([])
        ax2.invert_yaxis(); ax2.set_xlabel("eligible rows (0.1.3 → 0.1.4)")
        ax2.set_xlim(0, 720)
        ax2.set_title("B2  Contract repair effect", fontsize=8)
        ax2.scatter([], [], color=C_PRE, s=28, label="0.1.3")
        ax2.scatter([], [], color=C_LA, s=28, label="0.1.4")
        ax2.legend(fontsize=6.0, frameon=False, loc="lower right")
        fig.subplots_adjust(bottom=0.30)
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        save(fig, "figB_coverage")


def panel_c():
    pol = json.loads((EVAL / "expanded/policy_results/policy_summary.json").read_text())
    order = ["illinois", "indiana", "minnesota", "wisconsin", "mississippi", "iowa", "new_york", "ohio"]
    with (DATA / "panel_c_policy.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["export", "P0", "P1", "P4", "delta_P1", "delta_P4"])
        for o in order:
            v = pol[o]["variants"]
            w.writerow([o, v["P0"]["eligible"], v["P1"]["eligible"], v["P4"]["eligible"],
                        v["P1"]["eligible"] - v["P0"]["eligible"],
                        v["P4"]["eligible"] - v["P0"]["eligible"]])

    rows = list(csv.DictReader(open(EVAL / "expanded/downstream.tsv"), delimiter="\t"))
    key = {}
    for r in rows:
        if r["fit_status"] not in ("ok","ok_median_not_identified"):
            continue
        key[(r["export"], r["policy"], r["group"])] = r
    pairs = [("new_york", "109"), ("ohio", "13"), ("mississippi", "52")]
    # locate the P0/P1 group with the largest n and a finite estimate
    dvals = []
    for exp, _ in pairs:
        p0 = [r for r in rows if r["export"] == exp and r["policy"] == "P0" and r["fit_status"] in ("ok","ok_median_not_identified")]
        if not p0:
            continue
        g = max(p0, key=lambda r: int(r["n"]))["group"]
        a = next((r for r in rows if r["export"] == exp and r["policy"] == "P0" and r["group"] == g and r["fit_status"] in ("ok","ok_median_not_identified")), None)
        b = next((r for r in rows if r["export"] == exp and r["policy"] == "P1" and r["group"] == g and r["fit_status"] in ("ok","ok_median_not_identified")), None)
        if a and b:
            dvals.append((exp, a, b))
    with (DATA / "panel_c_downstream.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["export", "group", "n_P0", "mean_P0", "lcl_P0", "ucl_P0",
                                        "n_P1", "mean_P1", "lcl_P1", "ucl_P1"])
        for exp, a, b in dvals:
            w.writerow([exp, a["group"], a["n"], a["mean"], a["mean_lcl"], a["mean_ucl"],
                        b["n"], b["mean"], b["mean_lcl"], b["mean_ucl"]])

    with plt.rc_context(PLT):
        fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.9, 3.0), gridspec_kw={"width_ratios": [1.3, 1], "wspace": 0.38})
        base = [pol[o]["variants"]["P0"]["eligible"] for o in order]
        p1 = [pol[o]["variants"]["P1"]["eligible"] for o in order]
        p4 = [pol[o]["variants"]["P4"]["eligible"] for o in order]
        y = list(range(len(order)))
        for i in y:
            ax.plot([base[i], p1[i]], [i + 0.16, i - 0.16], color="#b9c3cf", lw=2, zorder=1)
            ax.scatter([base[i]], [i + 0.16], color=C_PRE, s=26, zorder=2)
            ax.scatter([p1[i]], [i - 0.16], color=C_BL, s=26, zorder=3)
            ax.scatter([p4[i]], [i], color=C_LA, marker="D", s=18, zorder=2)
            if p1[i] != base[i]:
                ax.text(p1[i] + 8, i - 0.25, f"+{p1[i]-base[i]}", fontsize=5.8, color=C_BL)
        ax.set_yticks(y); ax.set_yticklabels([o.replace("_", " ").title() for o in order], fontsize=6.8)
        ax.invert_yaxis(); ax.set_xlabel("eligible rows")
        ax.set_title("D1  Policy effect on eligible rows", fontsize=8)
        ax.scatter([], [], color=C_PRE, s=26, label="P0")
        ax.scatter([], [], color=C_BL, s=26, label="P1: all roles")
        ax.scatter([], [], color=C_LA, marker="D", s=20, label="P4: both fractions")
        ax.legend(fontsize=5.8, frameon=False, loc="lower right")

        labels = []
        for i, (exp, a, b) in enumerate(dvals):
            y0, y1 = i + 0.14, i - 0.14
            ax2.scatter(float(a["mean"]), y0, color=C_PRE, marker="o", s=18)
            ax2.scatter(float(b["mean"]), y1, color=C_BL, marker="o", s=18)
            ax2.annotate(f"{float(a['mean']):.3g}", (float(a["mean"]), y0),
                         textcoords="offset points", xytext=(-20, 0), ha="right", fontsize=5.6)
            ax2.annotate(f"{float(b['mean']):.3g}", (float(b["mean"]), y1),
                         textcoords="offset points", xytext=(8, 0), ha="left", fontsize=5.6)
            ax2.text(0.02, i + 0.30, f"{exp.replace('_',' ').title()} (n {a['n']}→{b['n']})",
                     transform=ax2.get_yaxis_transform(), fontsize=5.8, va="center")
        ax2.set_xscale("log")
        ax2.set_yticks([])
        ax2.set_ylim(-0.5, len(dvals) - 0.2)
        ax2.set_xticks([0.01, 0.1, 1.0]); ax2.set_xticklabels(["0.01", "0.1", "1.0"])
        ax2.xaxis.set_minor_formatter(NullFormatter())
        ax2.set_xlabel("group mean (ug/L, log scale)")
        ax2.set_title("D2  Downstream mean in matched groups", fontsize=8)
        fig.subplots_adjust(bottom=0.20)
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        save(fig, "figD_policy")
        return


def panel_d():
    agr = json.loads((EVAL / "expanded/results_0.1.4/agreement.json").read_text())["exports"]
    cols = ["Export", "Rows", "Eligible LA/BL", "Same set", "Max |Δ|", "Status diff\n(prec/subst)"]
    rows = []
    for r in agr:
        rows.append([r["export"].replace("_", " ").title(), str(r["rows"]),
                     f"{r['eligible_limitaware']} / {r['eligible_baseline']}",
                     "yes" if r["eligible_sets_identical"] else "NO",
                     f"{r['max_abs_observation_difference']:.1e}",
                     f"{r['status_differences_total']} ({r['precedence_differences']}/"
                     f"{r['substantive_differences']})"])
    with (DATA / "panel_d_agreement.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow([c.replace("\n", " ") for c in cols]); w.writerows(rows)
    with plt.rc_context(PLT):
        fig, ax = plt.subplots(figsize=(6.9, 3.0)); ax.axis("off")
        table = ax.table(cellText=[cols] + rows, cellLoc="center", bbox=[0.02, 0.18, 0.96, 0.72])
        table.auto_set_font_size(False); table.set_fontsize(6.9)
        for (r, c), cell in table.get_celld().items():
            cell.set_edgecolor("#c6ced8")
            if r == 0:
                cell.set_facecolor("#e8edf3"); cell.set_text_props(weight="bold")
        ax.set_title("C  Matched-baseline agreement on prepared input (eight exports)", fontsize=8.4, pad=4)
        ax.text(0.5, 0.04, "Censoring mismatches and grouping mismatches were zero for every export.\n"
                "Status differences are counts; parentheses give precedence / substantive. "
                "Max |Δ| is the largest absolute observation difference (unit conversion).",
                transform=ax.transAxes, ha="center", fontsize=5.9, color="#4d5c70", linespacing=1.4)
        save(fig, "figC_agreement")


def panel_e():
    b = json.loads((EVAL / "expanded/benchmark/benchmark.json").read_text())
    xs_la = [b["bench_933"]["rows"], b["bench_real"]["rows"], b["bench_10k"]["rows"]]
    ys_la = [b["bench_933"]["limitaware"]["median"], b["bench_real"]["limitaware"]["median"],
             b["bench_10k"]["limitaware"]["median"]]
    xs_bl = [b["bench_933"]["rows"], b["bench_real"]["rows"]]
    ys_bl = [b["bench_933"]["baseline"]["median"], b["bench_real"]["baseline"]["median"]]
    with (DATA / "panel_e_runtime.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["tool", "rows", "median_s"])
        for x, y in zip(xs_la, ys_la): w.writerow(["LimitAware 0.1.4", x, y])
        for x, y in zip(xs_bl, ys_bl): w.writerow(["baseline", x, y])
    with plt.rc_context(PLT):
        fig, ax = plt.subplots(figsize=(6.0, 2.8))
        ax.plot(xs_la, ys_la, marker="o", color=C_LA, label="LimitAware 0.1.4")
        ax.plot(xs_bl, ys_bl, marker="s", color=C_BL, label="baseline")
        for x, y in zip(xs_la, ys_la):
            ax.annotate(f"{y:.2f}s", (x, y), textcoords="offset points", xytext=(0, 6),
                        ha="center", fontsize=6.0)
        for x, y in zip(xs_bl, ys_bl):
            ax.annotate(f"{y:.2f}s", (x, y), textcoords="offset points", xytext=(-30, -14),
                        ha="center", fontsize=6.8)
        ax.set_xlabel("source rows", fontsize=9); ax.set_ylabel("median CLI wall time (s)", fontsize=9)
        ax.set_ylim(0, max(ys_la) * 1.25); ax.set_xlim(0, 11000)
        ax.legend(fontsize=7.2, frameon=False)
        ax.set_title("E  Runtime by workload (five runs)", fontsize=9)
        fig.tight_layout()
        save(fig, "figE_runtime")


if __name__ == "__main__":
    panel_a(); panel_b(); panel_c(); panel_d(); panel_e()
    print("figures:", sorted(p.name for p in OUT.glob("fig[A-E]*")))

# Reproducing LimitAware 0.1.4

Python 3.10+; R and NADA are needed only for the downstream/NADA checks.

## 1. Install and test

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install .
limitaware --version                      # limitaware 0.1.4
python -m unittest discover -s tests      # 62 tests
```

## 2. Analytical replay (held-out data are included)

```bash
python evaluation/run_expanded_study.py --stage all --workdir /tmp/la_replay
```

Stages: verify hashes → prepare P0–P5 → matched baseline → agreement →
policy transitions → NADA downstream → tables. Each stage is restartable
(`--stage prepare`, etc.). The driver recomputes results from archived inputs and
checks them against the shipped agreement/policy/downstream values; it does not copy
stored JSON. Requires Rscript with NADA for the downstream stage.

## 3. Development sidecar replay

Development downloads are not redistributed. Their raw-record sidecars are:

```bash
python evaluation/replay_from_sidecar.py iowa /tmp/la_sidecar
```

Status counts reproduce; the reconstructed CSV hash differs from the original
download hash (reported). This is replay from sidecars, not byte-identical
reconstruction.

## 4. EPATADA comparison (optional; R package installation required)

EPATADA 0.0.1 was installed from the pinned commit
`remotes::install_github("USEPA/EPATADA@f913d40298eb59ec07dfa78305cc777720f9a775")`
on 2026-10-26. The installed `RemoteSha` was verified as `f913d40298eb59ec07dfa78305cc777720f9a775`.

```bash
Rscript evaluation/epatada/run_comparison.R \
    evaluation/expanded/data/illinois_atrazine_2022.csv /tmp/il_flags.csv
```

Raw outputs from the study are in `evaluation/epatada/*_flags.csv`; the adapter
creates a source-instance `ResultIdentifier` because the WQP Result profile has none.

## 5. Figures and documents

```bash
pip install matplotlib python-docx
python evaluation/scripts/expanded_figures.py
python build_limitaware_docs.py
```

Documents need `pandoc` and LibreOffice (`soffice`). Run figures first; the document
builder rebuilds manuscript and supplement DOCX/PDF from the single Markdown source.

## 6. Evidence layout

* `evaluation/EXPANDED_PROTOCOL.md` — frozen protocol (hash in
  `EXPANDED_PROTOCOL.sha256`); deviations in `EXPANDED_DEVIATIONS.md`.
* `evaluation/STATISTICAL_AMENDMENT_2026-10-26.md` — estimands, dependence, KM audit.
* `evaluation/expanded/results_preRepair_0.1.3/`, `results_0.1.4/` — frozen and
  post-repair outputs.
* `evaluation/expanded/policy_results/` — six one-setting variants.
* `evaluation/expanded/semantic_audit.csv` — DL audit against the 2025 guidance.
* `evaluation/epatada/` — comparator provenance, raw flags and counts.
* `literature/raw/guidance/` — cached guidance PDF and hash.

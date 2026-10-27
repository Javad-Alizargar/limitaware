"""LimitAware web interface — imports the released package; no second parser."""
from __future__ import annotations
import io, json, os, pathlib, secrets, tempfile, threading, time, zipfile
from flask import Flask, abort, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

import limitaware
from limitaware import canonical, contract, output, policies

ROOT = pathlib.Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text())
POLICY_DIR = pathlib.Path(limitaware.__file__).resolve().parents[2] / "policies"
for candidate in (POLICY_DIR, ROOT.parent / "policies", ROOT.parent / "packages/limitaware/policies"):
    if candidate.exists():
        POLICY_DIR = candidate; break
POLICIES = {p.stem: policies.load(str(p)) for p in sorted(POLICY_DIR.glob("*.json")) if not p.name.startswith("._")}
MAX_BYTES = 2 * 1024 * 1024
RESULTS = {}
RESULT_LOCK = threading.Lock()
RESULT_TTL = int(os.environ.get("LIMITAWARE_RESULT_TTL", "600"))
MAX_RESULTS = 20

def _expire(token):
    with RESULT_LOCK:
        RESULTS.pop(token, None)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES


@app.context_processor
def inject_globals():
    return {"cfg": CONFIG, "version": limitaware.__version__}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/docs")
def docs():
    return render_template("docs.html", policies=sorted(POLICIES))


@app.get("/example")
def example():
    return render_template("example.html")


@app.get("/evaluation")
def evaluation():
    summary = json.loads((ROOT / "data/evaluation_summary.json").read_text())
    return render_template("evaluation.html", summary=summary)


@app.get("/limitations")
def limitations():
    return render_template("limitations.html")


@app.get("/cite")
def cite():
    return render_template("cite.html")


@app.get("/app")
def demo_form():
    return render_template("demo.html", policies=sorted(POLICIES), error=None)


def _transform(upload_bytes: bytes, filename: str, policy_name: str):
    if policy_name not in POLICIES:
        raise ValueError("unknown policy")
    with tempfile.TemporaryDirectory(prefix="limitaware-web-") as td:
        td = pathlib.Path(td)
        inp = td / "upload.csv"
        inp.write_bytes(upload_bytes)
        rows, header = contract.read_rows(inp)
        report = contract.check_columns(header)
        if not report["ok"]:
            raise ValueError("missing required columns: " + ", ".join(report["missing"]))
        policy = POLICIES[policy_name]
        records, summary = canonical.transform(rows, policy)
        out = td / "out"
        output.prepare_outdir(out, force=True)
        digest = contract.sha256(inp)
        for rec, raw in zip(records, rows):
            rec["source_sha256"] = digest
            raw["result_uid"] = rec["result_uid"]
        output.write_raw(rows, header, digest, out / "raw_records.csv")
        output.write_canonical(records, out / "canonical.csv")
        manifest = output.write_analysis(records, out)
        audit = output.build_audit(inp, report, policy, summary, {"provided": False})
        output.write_audit(audit, out / "audit.json")
        output.write_methods_note(audit, summary, manifest, out / "methods_note.md")
        (out / "policy.json").write_text(json.dumps(policy, indent=2))
        # Representative rows only; no data are retained after the request.
        sample = []
        for rec in records:
            if rec["status"] == "eligible" or len(sample) < 8:
                sample.append({k: rec.get(k) for k in
                               ("source_row", "status", "observation", "censored", "flags",
                                "analysis_group", "qualifier_raw", "condition_raw")})
            if len(sample) >= 12:
                break
        files = {p.name: p.read_bytes() for p in out.glob("*") if p.is_file()}
        meta = {"audit": audit, "manifest": manifest, "files": sorted(files),
                "sample": sample, "rows": len(records), "policy": policy_name,
                "filename": filename, "input_sha256": digest}
        return meta, files


@app.post("/app")
def demo_run():
    f = request.files.get("file")
    use_sample = request.form.get("use_sample") == "1"
    if use_sample:
        upload = (ROOT / "sample/interpretation_cases.csv").read_bytes()
        name = "interpretation_cases.csv"
    elif f and f.filename:
        name = pathlib.Path(f.filename).name
        if not name.lower().endswith(".csv"):
            return render_template("demo.html", policies=sorted(POLICIES),
                                   error="Upload a .csv result export."), 400
        upload = f.read(MAX_BYTES + 1)
        if len(upload) > MAX_BYTES:
            return render_template("demo.html", policies=sorted(POLICIES),
                                   error="File exceeds the 2 MB demo limit."), 413
    else:
        return render_template("demo.html", policies=sorted(POLICIES),
                               error="Choose a CSV file or load the included example."), 400
    try:
        meta, files = _transform(upload, name, request.form.get("policy", "reporting_total"))
    except (SystemExit, ValueError, OSError) as e:
        return render_template("demo.html", policies=sorted(POLICIES),
                               error=str(e)), 400
    # Store only a short-lived token in server memory is avoided: the zip is returned
    # immediately in a second self-contained response via a signed payload is overkill;
    # instead the result page posts back with the same file? Simpler: return a zip only.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)
    now = time.time()
    with RESULT_LOCK:
        for key in [k for k, v in RESULTS.items() if now - v[1] > RESULT_TTL]:
            RESULTS.pop(key, None)
        while len(RESULTS) >= MAX_RESULTS:
            RESULTS.pop(next(iter(RESULTS)))
        token = secrets.token_urlsafe(18)
        RESULTS[token] = (buf.getvalue(), now)
    timer = threading.Timer(RESULT_TTL, _expire, args=(token,))
    timer.daemon = True
    timer.start()
    return render_template("result.html", meta=meta, token=token)

@app.get("/download/<token>")
def download(token):
    with RESULT_LOCK:
        item = RESULTS.get(token)
    if not item:
        abort(404)
    data, created = item
    if time.time() - created > RESULT_TTL:
        RESULTS.pop(token, None)
        abort(404)
    return send_file(io.BytesIO(data), mimetype="application/zip", as_attachment=True,
                     download_name="limitaware_outputs.zip", max_age=0)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_):
    return render_template("demo.html", policies=sorted(POLICIES),
                           error="File exceeds the 2 MB demo limit."), 413


@app.get("/healthz")
def health():
    return {"status": "ok", "version": limitaware.__version__}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)

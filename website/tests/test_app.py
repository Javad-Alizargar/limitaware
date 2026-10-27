import io, pathlib, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"website"))
from app import app

def test_pages():
    c=app.test_client()
    for path in ("/","/docs","/example","/evaluation","/limitations","/cite","/app","/healthz"):
        r=c.get(path); assert r.status_code==200, (path,r.status_code)

def test_sample_and_download():
    c=app.test_client()
    r=c.post("/app", data={"use_sample":"1","policy":"reporting_total"}, content_type="multipart/form-data")
    assert r.status_code==200, r.data[:300]
    assert b"Interpretation result" in r.data
    # extract token from download link
    import re
    m=re.search(rb'/download/([A-Za-z0-9_-]+)', r.data); assert m
    z=c.get("/download/"+m.group(1).decode())
    assert z.status_code==200 and z.mimetype=="application/zip"
    zf=zipfile.ZipFile(io.BytesIO(z.data)); names=zf.namelist()
    for n in ("canonical.csv","raw_records.csv","audit.json","analysis_manifest.json"):
        assert n in names, names

def test_invalid_csv():
    c=app.test_client()
    r=c.post("/app", data={"file":(io.BytesIO(b"a,b\n1,2\n"),"bad.csv"),"policy":"reporting_total"},
             content_type="multipart/form-data")
    assert r.status_code==400
    assert b"missing required columns" in r.data

if __name__=="__main__":
    test_pages(); test_sample_and_download(); test_invalid_csv(); print("website tests ok")

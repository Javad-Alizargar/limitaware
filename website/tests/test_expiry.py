import io, os, pathlib, re, sys, time
os.environ["LIMITAWARE_RESULT_TTL"] = "1"
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"website"))
from app import app

def test_expiry():
    c=app.test_client()
    r=c.post("/app", data={"use_sample":"1","policy":"reporting_total"}, content_type="multipart/form-data")
    assert r.status_code==200
    m=re.search(rb'/download/([A-Za-z0-9_-]+)', r.data); assert m
    token=m.group(1).decode(); assert c.get("/download/"+token).status_code==200
    time.sleep(1.5)
    assert c.get("/download/"+token).status_code==404
if __name__=="__main__":
    test_expiry(); print("expiry test ok")

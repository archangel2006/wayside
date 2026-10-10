"""
audit_contracts.py  –  run from the wayside/ directory
python audit_contracts.py
"""
import gc, io, sys, time, traceback
import unittest.mock as mock
from PIL import Image, ImageDraw

try:
    import psutil
    PROC = psutil.Process()
    rss = lambda: PROC.memory_info().rss / 1024 / 1024
except ImportError:
    rss = lambda: -1.0

def section(t): print(f"\n{'='*60}\n  {t}\n{'='*60}")
def ok(m):   print(f"  [PASS] {m}")
def fail(m): print(f"  [FAIL] {m}")
def info(m): print(f"  [INFO] {m}")

def make_jpeg(w=300, h=400):
    img = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(img).ellipse([40, 60, 260, 340], fill=(80,160,80))
    buf = io.BytesIO(); img.save(buf, "JPEG"); buf.seek(0); return buf

section("1. API CONTRACT AUDIT  (mocked, no model weights needed)")

with mock.patch("app.services.vision.label_image",
                return_value={"label": "Green leaf", "description": "slightly crinkled"}):
    with mock.patch("app.services.story.generate_story",
                    return_value={"title": "The Quiet Walk", "text": "A leaf fell."}):
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)

r = client.get("/api/health")
(ok if r.status_code == 200 and r.json() == {"status":"ok"} else fail)(f"/api/health -> {r.status_code}")

buf = make_jpeg()
r = client.post("/api/cutout", files={"file": ("p.jpg", buf, "image/jpeg")})
if r.status_code == 200 and r.headers.get("content-type") == "image/png":
    img = Image.open(io.BytesIO(r.content))
    (ok if img.mode == "RGBA" else fail)(f"/api/cutout -> {img.mode} PNG {img.size}, {len(r.content)//1024}KB")
else:
    fail(f"/api/cutout -> {r.status_code} {r.text[:80]}")

with mock.patch("app.main.label_image",
                return_value={"label": "Green leaf", "description": "slightly crinkled"}):
    buf = make_jpeg()
    r = client.post("/api/label", files={"file": ("p.jpg", buf, "image/jpeg")})
d = r.json()
if r.status_code == 200 and "label" in d and "description" in d:
    ok(f"/api/label -> {d}")
else:
    fail(f"/api/label -> {r.status_code} {r.text[:80]}")

r = client.post("/api/label", files={"file": ("x.txt", io.BytesIO(b"garbage"), "text/plain")})
(ok if r.status_code == 400 else fail)(f"/api/label non-image -> {r.status_code}")

payload = {"items":[{"label":"Crumpled leaf","description":"spotted","note":"by the gate"},
                    {"label":"Smooth acorn","description":"round","note":""}],
           "theme":"mystery","place":"the old bridge"}
with mock.patch("app.main.generate_story",
                return_value={"title":"The Mystery Walk","text":"It was dark."}):
    r = client.post("/api/story", json=payload)
d = r.json()
if r.status_code == 200 and "title" in d and "text" in d:
    ok(f"/api/story -> {d}")
else:
    fail(f"/api/story -> {r.status_code} {r.text[:80]}")

r = client.post("/api/story")
(ok if r.status_code == 422 else fail)(f"/api/story no body -> {r.status_code}")

evil = {"items":[{"label":"x"*200,"description":"y"*200,"note":"z"*200}],
        "theme":"a"*200,"place":"b"*200}
with mock.patch("app.main.generate_story", return_value={"title":"Safe","text":"..."}):
    r = client.post("/api/story", json=evil)
(ok if r.status_code == 200 else fail)(f"/api/story overlong fields -> {r.status_code}")

section("2. PARALLEL FLOW - lock objects")
from app.limits import cutout_lock, vision_lock, story_lock
if cutout_lock is not vision_lock and vision_lock is not story_lock:
    ok("Three distinct asyncio.Locks -> cutout + label run in parallel")
else:
    fail("Some locks are shared -> parallel requests will serialize")

section("3. FALLBACK ACTIVATION  (model crash simulation)")
import app.services.vision as vis
import app.services.story  as sto
from app.services.vision import FALLBACK

orig_vload = vis._load_model
vis._load_model = lambda: (_ for _ in ()).throw(RuntimeError("OOM"))
try:
    r2 = vis.label_image(Image.new("RGB",(100,100),"green"))
    (ok if r2 == FALLBACK else fail)(f"vision fallback on crash -> {r2}")
except Exception as e:
    fail(f"vision raised instead of fallback: {e}")
finally:
    vis._load_model = orig_vload

orig_sload = sto._load_model
sto._load_model = lambda: (_ for _ in ()).throw(RuntimeError("OOM"))
try:
    r3 = sto.generate_story([{"label":"leaf","description":"g","note":""}],"quiet","park")
    (ok if "title" in r3 and "text" in r3 else fail)(f"story fallback on crash -> {r3}")
except Exception as e:
    fail(f"story raised instead of fallback: {e}")
finally:
    sto._load_model = orig_sload

print("\nContract audit complete.")

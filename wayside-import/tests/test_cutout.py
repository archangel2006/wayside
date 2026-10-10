import io
import os
import sys
import time
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_sample_image(size=(200, 200), color="red") -> io.BytesIO:
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 50, 150, 150], fill=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def test_cutout_success():
    buf = create_sample_image()
    
    # First call
    t0 = time.time()
    response1 = client.post(
        "/api/cutout",
        files={"file": ("sample.jpg", buf, "image/jpeg")}
    )
    t1 = time.time()
    call1_time = t1 - t0

    assert response1.status_code == 200, f"Expected 200, got {response1.status_code}: {response1.text}"
    assert response1.headers["content-type"] == "image/png"
    
    # Verify resulting image is valid RGBA PNG
    result_img = Image.open(io.BytesIO(response1.content))
    assert result_img.format == "PNG"
    assert result_img.mode == "RGBA"

    # Second call
    buf2 = create_sample_image()
    t2 = time.time()
    response2 = client.post(
        "/api/cutout",
        files={"file": ("sample2.jpg", buf2, "image/jpeg")}
    )
    t3 = time.time()
    call2_time = t3 - t2
    assert response2.status_code == 200

    print(f"[PASS] First cutout call time: {call1_time:.2f}s")
    print(f"[PASS] Second cutout call time: {call2_time:.2f}s")

def test_cutout_invalid_file():
    response = client.post(
        "/api/cutout",
        files={"file": ("fake.txt", io.BytesIO(b"not an image"), "text/plain")}
    )
    assert response.status_code == 400
    print("[PASS] Invalid file rejection tested")

if __name__ == "__main__":
    test_cutout_success()
    test_cutout_invalid_file()
    print("All cutout tests passed!")

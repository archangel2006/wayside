import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("[PASS] test_health_endpoint passed")

def test_static_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "Wayside" in response.text
    assert "collect your walk" in response.text
    print("[PASS] test_static_index passed")

def test_static_asset():
    response = client.get("/css/themes.css")
    assert response.status_code == 200
    assert "--bg" in response.text or "theme" in response.text
    print("[PASS] test_static_asset passed")

if __name__ == "__main__":
    test_health_endpoint()
    test_static_index()
    test_static_asset()
    print("All smoke tests passed successfully!")

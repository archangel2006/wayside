import argparse, statistics, sys, time, requests
from pathlib import Path

try:
    import psutil
    def get_ram():
        for proc in psutil.process_iter(['cmdline', 'memory_info']):
            cmd = " ".join(proc.info.get('cmdline') or [])
            if "uvicorn" in cmd or "app.main" in cmd:
                return f"{proc.info['memory_info'].rss / (1024**2):.0f} MB"
        return f"{psutil.Process().memory_info().rss / (1024**2):.0f} MB"
except Exception:
    def get_ram():
        return "not measured"

def time_call(fn):
    t0 = time.time()
    fn()
    return time.time() - t0

def bench_step(name, fn):
    t_first = time_call(fn)
    warm = [time_call(fn) for _ in range(3)]
    return name, f"{t_first:.1f} s", f"{statistics.median(warm):.1f} s"

def main():
    parser = argparse.ArgumentParser(description="Wayside local server benchmark")
    parser.add_argument("--photo", default="docs/sample.jpg", help="Path to sample photo")
    parser.add_argument("--url", default="http://127.0.0.1:7860", help="Base URL of server")
    args = parser.parse_args()

    photo_path = Path(args.photo)
    if not photo_path.exists():
        print(f"Sample photo missing at '{photo_path}'. Please add docs/sample.jpg or pass --photo PATH.")
        sys.exit(1)

    url, img_bytes = args.url.rstrip("/"), photo_path.read_bytes()
    def do_cutout():
        r = requests.post(f"{url}/api/cutout", files={"file": ("photo.jpg", img_bytes, "image/jpeg")}, timeout=120)
        r.raise_for_status()
    def do_label():
        r = requests.post(f"{url}/api/label", files={"file": ("photo.jpg", img_bytes, "image/jpeg")}, timeout=120)
        r.raise_for_status()
    def do_story():
        items = [{"label": "Maple leaf", "desc": "on path", "note": "crisp red leaf"},
                 {"label": "Acorn", "desc": "under oak", "note": "cap askew"},
                 {"label": "Pebble", "desc": "near stream", "note": "smooth"}]
        r = requests.post(f"{url}/api/story", json={"items": items, "theme": "quiet", "place": "old trail"}, timeout=120)
        r.raise_for_status()
    def do_cover():
        r = requests.post(f"{url}/api/cover", json={"title": "Trail Walk", "text": "A quiet autumn walk along the path.", "theme": "quiet", "place": "old trail", "labels": ["Maple leaf", "Acorn", "Pebble"]}, timeout=180)
        r.raise_for_status()

    steps = [("Cutout (rembg u2netp)", do_cutout), ("Label (SmolVLM-256M)", do_label),
             ("Story (Qwen2.5-0.5B)", do_story), ("Cover (SD-Turbo 2 steps)", do_cover)]
    rows = [bench_step(name, fn) for name, fn in steps]

    print(f"\nPeak RAM: {get_ram()}\n")
    print("| Step | First call | Warm call (median) |")
    print("| :--- | :--- | :--- |")
    for name, f, w in rows:
        print(f"| {name} | {f} | {w} |")

if __name__ == "__main__":
    main()

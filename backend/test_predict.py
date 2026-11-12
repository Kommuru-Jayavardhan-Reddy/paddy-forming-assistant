import sys
from pathlib import Path
import requests

URL = "http://127.0.0.1:8000/predict"
root = Path(sys.argv[1])
ok = total = 0

for img in sorted(root.rglob("*")):
    if img.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        continue
    true = img.parent.name
    with open(img, "rb") as f:
        r = requests.post(URL, files={"file": f})
    if r.status_code != 200:
        print(f"{img.name:25} ERROR {r.status_code} {r.text[:80]}")
        continue
    d = r.json()
    pred = d["disease"]
    total += 1
    ok += pred == true
    mark = "OK " if pred == true else "BAD"
    print(f"{mark} {img.name:22} true={true:24} pred={pred:24} conf={d['confidence']}")

print(f"\n{ok}/{total} correct ({100*ok/max(total,1):.1f}%)")
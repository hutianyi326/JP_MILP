"""Resolve Kyushu's observed dynamic public index, then inspect one listed CSV."""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
base = "https://www.kyuden.co.jp/td_power_usages/"
index_url = urljoin(base, "csv/lfc/kouiki_lfc_info_list.csv")

def get(url, key):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "samples" / (key + "_" + digest[:12] + ".csv")
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(payload)
    return payload, {"url": url, "path": str(path.relative_to(root)), "sha256": digest, "bytes": len(payload), "access_utc": datetime.now(timezone.utc).isoformat()}

index_bytes, index_info = get(index_url, "kyushu_lfc_index")
index = index_bytes.decode("utf-8-sig")
files = re.findall(r"jukyu_LFC_kyushu_\d{6}\.csv", index)
print("Listed filenames:", files)
result = {"index": index_info, "listed_files": files}
selected = next((name for name in files if "202606" in name), None)
if selected:
    payload, sample_info = get(urljoin(base, "csv/lfc/" + selected), "kyushu_lfc_202606")
    for encoding in ("utf-8-sig", "cp932"):
        try:
            content = payload.decode(encoding)
            break
        except UnicodeError:
            continue
    rows = list(csv.reader(io.StringIO(content)))
    dated = [r for r in rows if r and r[0].isdigit() and len(r[0]) == 8]
    sample_info.update({"encoding": encoding, "header": rows[0], "dated_rows": len(dated), "unique_keys": len({(r[0], r[1]) for r in dated}), "first_row": dated[0], "last_row": dated[-1], "slot_values": sorted({int(r[1]) for r in dated})})
    result["sample"] = sample_info
else:
    result["unresolved"] = "June 2026 is not present in the public index"
(root / "kyushu_dynamic_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))

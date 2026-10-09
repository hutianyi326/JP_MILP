"""Validate the seven inspected June CSV datasets without interpreting activation."""
import csv
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
expected = {(date(2026, 6, day).strftime("%Y%m%d"), str(slot)) for day in range(1, 31) for slot in range(1, 49)}
sources = []
for filename in ("sample_manifest.json", "sample_manifest_extra.json"):
    sources.extend(x for x in json.loads((root / filename).read_text(encoding="utf-8")) if "inspection" in x)
sources.append(json.loads((root / "kyushu_dynamic_manifest.json").read_text(encoding="utf-8"))["sample"])
results = []
for source in sources:
    payload = (root / source["path"]).read_bytes()
    hash_ok = hashlib.sha256(payload).hexdigest() == source["sha256"]
    members = [(Path(source["path"]).name, payload)]
    if payload[:2] == b"PK":
        archive = zipfile.ZipFile(io.BytesIO(payload))
        members = [(n, archive.read(n)) for n in archive.namelist() if n.lower().endswith(".csv")]
    for name, content in members:
        records = list(csv.reader(io.StringIO(content.decode("cp932"))))
        header = records[0]
        dated = [r for r in records if r and r[0].isdigit() and len(r[0]) == 8]
        keys = [(r[0], r[1]) for r in dated]
        result = {"file": source["path"], "member": name, "sha256_ok": hash_ok, "rows": len(dated), "columns": len(header), "expected_month_keys_ok": set(keys) == expected, "duplicate_keys": len(keys) - len(set(keys)), "wrong_width_rows": sum(len(r) != len(header) for r in dated), "blank_numeric_cells": sum(not x.strip() for r in dated for x in r[4:])}
        result["structural_pass"] = hash_ok and result["expected_month_keys_ok"] and result["duplicate_keys"] == 0 and result["wrong_width_rows"] == 0
        results.append(result)
summary = {"datasets": len(results), "structural_passes": sum(r["structural_pass"] for r in results), "results": results, "scope": "Original bytes, June 2026 date/slot coverage, duplicate keys, field widths and blank cells only; not validation of physical activation semantics or historical revision availability."}
(root / "validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))

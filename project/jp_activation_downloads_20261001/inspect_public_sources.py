"""Inspect a small, explicitly selected set of public TSO downloads, not a bulk crawler."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
PAGES = {
    "kyushu_lfc": "https://www.kyuden.co.jp/td_power_usages/lfc_list.html",
    "kyushu_jukyu": "https://www.kyuden.co.jp/td_power_usages/jukyuchosei_list.html",
    "tokyo": "https://www.tepco.co.jp/forecast/html/adjust-j.html",
    "chubu": "https://powergrid.chuden.co.jp/goannai/hatsuden_kouri/takuso_kyokyu/rule/jukyu/",
    "tohoku": "https://nw.tohoku-epco.co.jp/consignment/retailservice/supplyanddemand/",
    "hokuriku": "https://www.rikuden.co.jp/nw_jyukyudata/jukyutyousei.html",
    "shikoku": "https://www.yonden.co.jp/nw/adjusting_power_supply/supply_demand.html",
    "kansai": "https://www.kansai-td.co.jp/denkiyoho/implementation-status/past.html",
}

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []
    def handle_data(self, data):
        if self.href is not None:
            self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, "".join(self.parts).strip()))
            self.href = None

def fetch(item):
    key, url = item
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = response.read()
            final_url = response.url
        digest = hashlib.sha256(payload).hexdigest()
        ext = ".zip" if payload[:2] == b"PK" else (".html" if key in PAGES else ".csv")
        filename = key + "_" + digest[:12] + ext
        destination = ROOT / "samples" / filename
        destination.parent.mkdir(exist_ok=True)
        if not destination.exists():
            with destination.open("xb") as stream:
                stream.write(payload)
        info = {"id": key, "url": url, "final_url": final_url, "path": str(destination.relative_to(ROOT)), "sha256": digest, "bytes": len(payload), "access_utc": datetime.now(timezone.utc).isoformat()}
        if key in PAGES:
            decoded = payload.decode("utf-8", errors="replace")
            parser = Links()
            parser.feed(decoded)
            info["download_links"] = [{"url": urljoin(final_url, href), "label": label} for href, label in parser.links if any(s in href.lower() for s in (".csv", ".zip", "lfc"))]
        else:
            members = [(filename, payload)]
            if ext == ".zip":
                archive = zipfile.ZipFile(io.BytesIO(payload))
                members = [(n, archive.read(n)) for n in archive.namelist() if n.lower().endswith(".csv")]
            inspected = []
            for name, data in members:
                encoding = None
                for candidate in ("utf-8-sig", "cp932", "utf-16"):
                    try:
                        content = data.decode(candidate)
                        encoding = candidate
                        break
                    except UnicodeError:
                        continue
                if encoding is None:
                    raise ValueError("Unrecognized CSV encoding")
                rows = list(csv.reader(io.StringIO(content)))
                date_rows = [r for r in rows if r and r[0].strip().isdigit() and len(r[0].strip()) == 8]
                item_info = {"member": name, "encoding": encoding, "total_rows": len(rows), "dated_rows": len(date_rows), "first_rows": rows[:6], "last_rows": rows[-2:]}
                if date_rows:
                    keys = [(r[0], r[1]) for r in date_rows]
                    item_info.update({"unique_keys": len(set(keys)), "first_key": keys[0], "last_key": keys[-1], "slot_values": sorted(set(k[1] for k in keys), key=lambda v:int(v) if v.isdigit() else 9999)})
                inspected.append(item_info)
            info["inspection"] = inspected
        return info
    except Exception as error:
        return {"id": key, "url": url, "error": str(error)}

if sys.argv[1] in ("pages", "extra_pages"):
    extra = sys.argv[1] == "extra_pages"
    items = [(key, value) for key, value in PAGES.items() if (key in ("shikoku", "kansai")) == extra]
    name = "extra_pages_manifest.json" if extra else "pages_manifest.json"
else:
    extra = sys.argv[1] == "extra_samples"
    config = json.loads((ROOT / ("selected_samples_extra.json" if extra else "selected_samples.json")).read_text(encoding="utf-8"))
    items = list(config.items())
    name = "sample_manifest_extra.json" if extra else "sample_manifest.json"
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(fetch, items))
(ROOT / name).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
for result in results:
    if "download_links" in result:
        links = result["download_links"]
        selected = [x for x in links if "lfc" in x["url"].lower() or "202606" in x["url"] or "2026年6月" in x["label"] or "202606" in x["label"]]
        print(json.dumps({"id": result["id"], "bytes": result["bytes"], "links": selected}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))

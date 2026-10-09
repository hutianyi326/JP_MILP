from pathlib import Path
import csv,io,zipfile,json,collections
root=Path(__file__).resolve().parents[2]
def parse(p):
    data=p.read_bytes()
    for enc in ["utf-8-sig","cp932"]:
        try: return list(csv.reader(io.StringIO(data.decode(enc)))),enc
        except UnicodeDecodeError: pass
for rel in [
"project/jp_activation_downloads_20261001/samples/kyushu_lfc_202606_4c5f53588b32.csv",
"data/raw/JP/activation_sources_20261001/ics_basis_202606.csv"]:
    rows,enc=parse(root/rel)
    print(json.dumps({"file":rel,"encoding":enc,"rows":len(rows),"header":list(enumerate(rows[0],1)),"first_data":rows[1][:5]},ensure_ascii=False))
p=root/"countries/JP/research/analysis/eprx_awards_native_blocks_expost.csv"
with p.open(encoding="utf-8-sig",newline="") as f:
    rows=[r for r in csv.DictReader(f) if r["timestamp_JST"].startswith("2026-06") and r["area"]=="九州"]
groups=collections.defaultdict(list)
for r in rows: groups[r["product"]].append(r)
print(json.dumps({"capacity_products":{k:{"rows":len(v),"first":v[0],"last_time":v[-1]["timestamp_JST"]} for k,v in groups.items()}},ensure_ascii=False))


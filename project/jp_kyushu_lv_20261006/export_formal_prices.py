"""Export the requested formal period without the September observation tail."""
from pathlib import Path
import csv, hashlib, json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
SOURCE = ROOT / 'data/processed/JP/kyushu_lv_20251201_20260831_v1/market_prices_30min.csv'

def main():
    with SOURCE.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = [row for row in reader if row['period_role'] == 'formal']
    assert len(rows) == 13152
    assert len({row['timestamp_jst'] for row in rows}) == len(rows)
    assert rows[0]['timestamp_jst'] == '2025-12-01T00:00:00+09:00'
    assert rows[-1]['timestamp_jst'] == '2026-08-31T23:30:00+09:00'
    assert all(row['area'] == '九州' and row['quality'] == '確報値' for row in rows)
    destination = HERE / '九州现货与一次离线电价_20251201_20260831.csv'
    with destination.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(dict(rows=len(rows),file=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest()),ensure_ascii=False))

if __name__ == '__main__':
    main()

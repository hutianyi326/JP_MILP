from pathlib import Path
import hashlib, json
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SOURCES = {
    'E02': 'E02_1c1881b3a21a.pdf',
    'E03': 'E03_1b34e85ca8f2.pdf',
    'E04': 'E04_188e7ef84dd0.pdf',
}
manifest = []
for key, name in SOURCES.items():
    source = ROOT / 'countries/JP/research/evidence' / name
    reader = PdfReader(source)
    pages = [p.extract_text() or '' for p in reader.pages]
    (BASE / f'{key}_pages.json').write_text(json.dumps(pages, ensure_ascii=False), encoding='utf-8')
    (BASE / f'{key}_extracted.txt').write_text('\n\n'.join(f'=== PDF PAGE {i+1} ===\n{t}' for i,t in enumerate(pages)), encoding='utf-8')
    manifest.append({'id': key, 'source': str(source.relative_to(ROOT)), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'pdf_pages': len(pages)})
(BASE / 'source_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=True, indent=2))

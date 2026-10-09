from pathlib import Path
import pypdfium2 as pdfium

base = Path(__file__).resolve().parent
root = base.parents[1]
jobs = {
    'E02_1c1881b3a21a.pdf': [361, 363],
    'E03_1b34e85ca8f2.pdf': [241, 397],
    'E04_188e7ef84dd0.pdf': [21, 23],
}
out = base / 'visual_checks'
out.mkdir(exist_ok=True)
for name, pages in jobs.items():
    doc = pdfium.PdfDocument(root / 'countries/JP/research/evidence' / name)
    for number in pages:
        page = doc[number-1]
        bitmap = page.render(scale=1.7)
        bitmap.to_pil().save(out / f'{name[:3]}_p{number}.png')
        bitmap.close()
        page.close()
    doc.close()
print('Rendered six evidence pages.')

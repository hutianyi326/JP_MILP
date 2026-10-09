import pathlib, zipfile, csv, io, sys, collections, json, hashlib, calendar

sys.stdout.reconfigure(encoding='utf-8')
root = pathlib.Path(__file__).resolve().parents[4]
raw = root / 'data/raw/JP/shikoku_20260930'
reports, manifest = [], []
for f in sorted(raw.iterdir()):
    if f.suffix not in ('.csv', '.zip'):
        continue
    manifest.append({'file':f.name, 'bytes':f.stat().st_size,
        'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
        'url':'https://www.yonden.co.jp/nw/assets/adjusting_power_supply/'+('2026' if f.suffix=='.csv' else f.stem[-4:])+'/'+f.name,
        'access_date':'2026-09-30'})
    if f.suffix == '.csv':
        entries = [(f.name, f.read_bytes())]
    else:
        with zipfile.ZipFile(f) as z:
            entries = [(n,z.read(n)) for n in z.namelist() if n.endswith('.csv')]
    for name, b in entries:
        month = pathlib.Path(name).stem[-6:]
        if not '202501' <= month <= '202608':
            continue
        encoding = 'utf-8-sig' if b.startswith(b'\xef\xbb\xbf') else 'cp932'
        rows = list(csv.reader(io.StringIO(b.decode(encoding))))
        h, rs = rows[0], [r for r in rows[1:] if r]
        keys = [(r[0],r[1]) for r in rs]
        blanks = [r[:4] for r in rs if all(not x.strip() for x in r[4:])]
        bad = [r[:7] for r in rs if 'LFC' in name and r[4] and abs(float(r[4]))>1]
        expected = {(month+str(day).zfill(2),str(slot))
            for day in range(1,calendar.monthrange(int(month[:4]),int(month[4:]))[1]+1)
            for slot in range(1,49)}
        report = {'file':name,'archive':f.name,'encoding':encoding,'rows':len(rs),'columns':len(h),
            'headers':h,'first':rs[0],'last':rs[-1],
            'duplicate_keys':len(keys)-len(set(keys)), 'missing_keys':len(expected-set(keys)),
            'unexpected_keys':len(set(keys)-expected),
            'row_width_errors':sum(len(r)!=len(h) for r in rs),
            'all_value_blank_rows':len(blanks),
            'blank_cells':sum(not x.strip() for r in rs for x in r[4:]),
            'all_value_blank_by_day':dict(collections.Counter(r[0] for r in blanks)),
            'first_nonblank':next((r for r in rs if any(x.strip() for x in r[4:])),None),
            'frequency_abs_mean_gt_1Hz_count':len(bad),'frequency_flag_examples':bad[:3]}
        reports.append(report)
        print(name, 'rows',len(rs),'missingkeys',report['missing_keys'],
              'blankrows',len(blanks),'blankcells',report['blank_cells'],'freqflags',len(bad))
out = pathlib.Path(__file__).parent
(out/'file_audit.json').write_text(json.dumps({
    'access_date':'2026-09-30','timezone_assumption':'Asia/Tokyo; domestic delivery slots, verify source specification before production',
    'frequency_flag':'abs(mean frequency deviation)>1 Hz is an audit heuristic, not an official threshold; no automatic correction',
    'files':reports},ensure_ascii=False,indent=2),encoding='utf-8')
(out/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

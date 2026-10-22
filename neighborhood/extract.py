import csv, gzip, sys, json, glob, os
csv.field_size_limit(sys.maxsize)
raw, out = sys.argv[1], sys.argv[2]
ORIG = {'29007': 'Audrain', '29019': 'Boone', '29151': 'Osage'}
COLS = ['DEVICE_HOME_AREAS', 'WEEKDAY_DEVICE_HOME_AREAS', 'WEEKEND_DEVICE_HOME_AREAS',
        'WORK_HOURS_DEVICE_HOME_AREAS', 'WORK_BEHAVIOR_DEVICE_HOME_AREAS']
with open(out, 'w', newline='') as fo:
    w = csv.writer(fo)
    w.writerow(['month', 'dest_cbg', 'dest_county', 'home_cbg', 'home_county', 'home_county_name'] + [c.lower() for c in COLS])
    for path in sorted(glob.glob(os.path.join(raw, '*.csv.gz'))):
        n = 0
        with gzip.open(path, 'rt', newline='') as f:
            for r in csv.DictReader(f):
                parsed = {c: json.loads(r[c] or '{}') for c in COLS}
                homes = {h for h in parsed['DEVICE_HOME_AREAS'] if h[:5] in ORIG}
                for c in COLS[1:]:
                    homes |= {h for h in parsed[c] if h[:5] in ORIG}
                for h in sorted(homes):
                    w.writerow([r['DATE_RANGE_START'][:7], r['AREA'], r['AREA'][:5], h, h[:5], ORIG[h[:5]]] + [parsed[c].get(h, 0) for c in COLS])
                    n += 1
        print(os.path.basename(path)[:10], n, 'flows', flush=True)

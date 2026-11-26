#!/usr/bin/env python3
"""One-off: download CBUAE monthly Excel files listed in backfill/urls.txt and
save every (date, currency name, rate) row to backfill/raw.json for review."""
import datetime, json, sys, urllib.request, io
import openpyxl

rows, errors = [], []
for url in open("backfill/urls.txt").read().split():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (aed-converter backfill)"})
        data = urllib.request.urlopen(req, timeout=60).read()
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        n = 0
        for ws in wb:
            for r in ws.iter_rows(values_only=True):
                if not r or len(r) < 3 or r[2] is None:
                    continue
                d, name, val = r[0], r[1], r[2]
                if isinstance(d, str):
                    for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            d = datetime.datetime.strptime(d.strip(), fmt); break
                        except ValueError:
                            pass
                if not isinstance(d, datetime.datetime):
                    continue
                try:
                    val = float(val)
                except (TypeError, ValueError):
                    continue
                rows.append([d.strftime("%Y-%m-%d"), str(name).strip(), val]); n += 1
        print(url.rsplit("/", 1)[-1], n, "rows")
    except Exception as e:
        errors.append(f"{url}: {e}"); print("ERROR", url, e)
json.dump({"rows": rows, "errors": errors}, open("backfill/raw.json", "w"), separators=(",", ":"))
print("total", len(rows), "errors", len(errors))

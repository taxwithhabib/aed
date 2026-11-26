#!/usr/bin/env python3
"""Fetch today's CBUAE exchange rates against AED and add them to the site data.

Updates rates.json (latest day), hist/YYYY-MM.json (one file per month) and
hist/index.json. Standard library only. Run from the repository root:

    python scripts/update_rates.py            # fetch from CBUAE
    python scripts/update_rates.py --file x   # parse a saved CBUAE page instead
"""
import argparse, datetime, html, json, os, re, sys, urllib.request

URL = "https://www.centralbank.ae/umbraco/Surface/Exchange/GetExchangeRateAllCurrency?lang=en"
SOURCE_URL = "https://www.centralbank.ae/en/forex-eibor/exchange-rates/"
VOLATILE = {"LBP", "IRR", "SYP", "SDG", "NGN", "ARS", "EGP", "TRY", "ETB"}

# CBUAE currency names -> ISO 4217 codes (CBUAE's own spelling, e.g. "Bahrani Dinar")
NAMES = {
 "US Dollar": "USD",
 "Argentine Peso": "ARS",
 "Australian Dollar": "AUD",
 "Bangladesh Taka": "BDT",
 "Bahrani Dinar": "BHD",
 "Brunei Dollar": "BND",
 "Brazilian Real": "BRL",
 "Botswana Pula": "BWP",
 "Belarus Rouble": "BYN",
 "Canadian Dollar": "CAD",
 "Swiss Franc": "CHF",
 "Chilean Peso": "CLP",
 "Chinese Yuan - Offshore": "CNH",
 "Chinese Yuan": "CNY",
 "Colombian Peso": "COP",
 "Czech Koruna": "CZK",
 "Danish Krone": "DKK",
 "Algerian Dinar": "DZD",
 "Egypt Pound": "EGP",
 "Euro": "EUR",
 "GB Pound": "GBP",
 "Hongkong Dollar": "HKD",
 "Hungarian Forint": "HUF",
 "Indonesia Rupiah": "IDR",
 "Indian Rupee": "INR",
 "Iceland Krona": "ISK",
 "Jordan Dinar": "JOD",
 "Japanese Yen": "JPY",
 "Kenya Shilling": "KES",
 "Korean Won": "KRW",
 "Kuwaiti Dinar": "KWD",
 "Kazakhstan Tenge": "KZT",
 "Lebanon Pound": "LBP",
 "Sri Lanka Rupee": "LKR",
 "Moroccan Dirham": "MAD",
 "Macedonia Denar": "MKD",
 "Mexican Peso": "MXN",
 "Malaysia Ringgit": "MYR",
 "Nigerian Naira": "NGN",
 "Norwegian Krone": "NOK",
 "NewZealand Dollar": "NZD",
 "Omani Rial": "OMR",
 "Peru Sol": "PEN",
 "Philippine Piso": "PHP",
 "Pakistan Rupee": "PKR",
 "Polish Zloty": "PLN",
 "Qatari Riyal": "QAR",
 "Serbian Dinar": "RSD",
 "Russia Rouble": "RUB",
 "Saudi Riyal": "SAR",
 "Sudanese Pound": "SDG",
 "Swedish Krona": "SEK",
 "Singapore Dollar": "SGD",
 "Thai Baht": "THB",
 "Tunisian Dinar": "TND",
 "Turkish Lira": "TRY",
 "Trin Tob Dollar": "TTD",
 "Taiwan Dollar": "TWD",
 "Tanzania Shilling": "TZS",
 "Uganda Shilling": "UGX",
 "Vietnam Dong": "VND",
 "Yemen Rial": "YER",
 "South Africa Rand": "ZAR",
 "Zambian Kwacha": "ZMW",
 "Azerbaijan manat": "AZN",
 "Bulgarian lev": "BGN",
 "Ethiopian birr": "ETB",
 "Iraqi dinar": "IQD",
 "Israeli new shekel": "ILS",
 "Libyan dinar": "LYD",
 "Mauritian rupee": "MUR",
 "Nepalese rupee": "NPR",
 "Romanian leu": "RON",
 "Syrian pound": "SYP",
 "Turkmen manat": "TMT",
 "Uzbekistani som": "UZS",
 "Iranian rial": "IRR",
 "Croatian kuna": "HRK"
}


def norm(s):
    return re.sub(r"\s+", "", s).lower()


CODES = {norm(k): v for k, v in NAMES.items()}


def fetch():
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (aed-converter rate updater)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # network hiccup - retry
            last = e
    sys.exit(f"Could not reach CBUAE: {last}")


def parse(page):
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", page)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text)
    m = re.search(r"Last updated:\s*(\w+day \d{1,2} \w+ \d{4} \d{1,2}:\d{2}:\d{2} [AP]M)", text)
    if not m:
        sys.exit("CBUAE page has no 'Last updated' line - layout may have changed")
    updated_text = m.group(1)
    when = datetime.datetime.strptime(updated_text, "%A %d %B %Y %I:%M:%S %p")
    body = text.split("Currency Rates", 1)[-1]
    rates, unknown = [], []
    for name, val in re.findall(r"([A-Za-z][A-Za-z .\-]*?)\s+([0-9]+(?:\.[0-9]+)?(?:[Ee]-?[0-9]+)?)\b", body):
        name = name.strip()
        code = CODES.get(norm(name))
        if not code:
            unknown.append(name)
            continue
        if code not in {x["code"] for x in rates}:
            rates.append({"name": name, "code": code, "aed": float(val)})
    return updated_text, when, rates, unknown


def load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save(path, data, compact=False):
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(data, f, indent=1, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="parse a saved CBUAE page instead of downloading it")
    args = ap.parse_args()
    page = open(args.file, encoding="utf-8").read() if args.file else fetch()
    updated_text, when, rates, unknown = parse(page)
    if unknown:
        print("WARNING - currency names not recognised (skipped, add them to NAMES):", ", ".join(sorted(set(unknown))))
    day = when.strftime("%Y-%m-%d")

    prev = load("rates.json", {"rates": []})
    if prev.get("cbuaeUpdatedText") == updated_text:
        print(f"No new CBUAE rates (still {updated_text}).")
        return

    # sanity checks - refuse to publish obviously broken data
    by = {x["code"]: x["aed"] for x in rates}
    problems = []
    if len(rates) < 60:
        problems.append(f"only {len(rates)} currencies found")
    if not 3.67 <= by.get("USD", 0) <= 3.675:
        problems.append(f"USD rate {by.get('USD')} outside 3.67-3.675")
    for x in prev.get("rates", []):
        new = by.get(x["code"])
        if new and x["aed"] and x["code"] not in VOLATILE and not 0.75 <= new / x["aed"] <= 1.25:
            problems.append(f"{x['code']} moved from {x['aed']} to {new}")
    if problems:
        sys.exit("Not updating - data looks wrong: " + "; ".join(problems))

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4)))
    save("rates.json", {
        "source": "Central Bank of the UAE - Exchange rates against UAE Dirham",
        "sourceUrl": SOURCE_URL,
        "cbuaeUpdated": when.strftime("%Y-%m-%dT%H:%M:%S+04:00"),
        "cbuaeUpdatedText": updated_text,
        "rateDate": day,
        "fetchedAt": now.strftime("%Y-%m-%dT%H:%M:%S+04:00"),
        "rates": rates,
    })

    os.makedirs("hist", exist_ok=True)
    month = day[:7]
    mpath = f"hist/{month}.json"
    mdata = load(mpath, {"month": month, "days": {}})
    mdata["days"][day] = by
    mdata["days"] = dict(sorted(mdata["days"].items()))
    save(mpath, mdata, compact=True)

    idx = load("hist/index.json", {"first": day, "last": day, "months": [], "names": {}})
    if month not in idx["months"]:
        idx["months"] = sorted(idx["months"] + [month])
    if day > idx.get("last", ""):
        idx["last"] = day
    for x in rates:
        idx["names"].setdefault(x["code"], x["name"])
    save("hist/index.json", idx, compact=True)

    print(f"Added CBUAE rates for {day} ({len(rates)} currencies). USD {by.get('USD')}, EUR {by.get('EUR')}, GBP {by.get('GBP')}")


if __name__ == "__main__":
    main()

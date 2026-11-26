# CBUAE AED Converter

Live: https://taxwithhabib.github.io/aed/

Created by Ahmed Saeed Habib

Converts any currency published by the Central Bank of the UAE (CBUAE) into UAE Dirham, and back, at the CBUAE rate for any business day since 1 January 2018.

- `index.html` - the converter page
- `rates.json` - latest CBUAE rates
- `hist/` - one file per month of daily rates, plus `index.json`
- `scripts/update_rates.py` - fetches the day's rates from CBUAE and adds them to the files
- `.github/workflows/update-rates.yml` - runs the script every weekday evening and saves the result

Source: https://www.centralbank.ae/en/forex-eibor/exchange-rates/ (rates published for VAT-related obligations, Monday to Friday, based on 6pm UAE time).

name: Dual Market Scanner
on:
  schedule:
    # Runs Crypto bot every day at 12:00 PM UTC (Noon)
    - cron: '0 12 * * *'
    # Runs Stock bot Monday-Friday at 9:00 PM UTC (5:00 PM EST, after market close)
    - cron: '0 21 * * 1-5'
  workflow_dispatch: {}

jobs:
  run-crypto:
    runs-on: ubuntu-latest
    if: github.event.schedule == '0 12 * * *' || github.event_name == 'workflow_dispatch'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - run: python bot.py

  run-stocks:
    runs-on: ubuntu-latest
    if: github.event.schedule == '0 21 * * 1-5' || github.event_name == 'workflow_dispatch'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - run: python stock_bot.py

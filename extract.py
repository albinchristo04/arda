name: Fetch Daddylive Events

on:
  workflow_dispatch:   # run manually
  schedule:
    - cron: "0 * * * *" # every hour

jobs:
  fetch:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4

      - name: Run extractor
        run: python extract.py

      - name: Commit events.json
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add events.json
          git commit -m "Update events.json" || echo "No changes"
          git push

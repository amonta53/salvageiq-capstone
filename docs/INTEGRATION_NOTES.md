# SalvageIQ App Starter

## What this adds

This starter adds a thin FastAPI layer and a simple Bootstrap UI around the existing SalvageIQ pipeline.

New files:

```text
app/
  api.py
  salvage_service.py
  vehicle_lookup.py
  static/
    index.html
    script.js
    style.css
requirements_app.txt
```

## How to install

Copy the `app` folder and `requirements_app.txt` into the root of the existing `salvageiq-capstone-main` project.

Then run:

```bash
pip install -r requirements_app.txt
playwright install chromium
uvicorn app.api:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Important design choices

1. The browser should never call `backend.bat` directly.
2. API secrets should never live in HTML, JavaScript, or batch files.
3. The app calls the existing Python pipeline directly.
4. First working model is one vehicle, one year, full softcoded part list, ranked output.
5. VIN decode currently uses NHTSA vPIC because it does not require credentials.

## Next obvious improvements

1. Add a run cache so the same vehicle does not rescrape immediately.
2. Add async job status because full scraping can take a while.
3. Store results in SQLite or Postgres instead of only CSV.
4. Add fitment, trim, and engine filtering.
5. Move scrape execution to a worker queue.

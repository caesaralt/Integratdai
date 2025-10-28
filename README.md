# 🏠 Lock Zone AI Floor Plan Analyzer

Lock Zone AI analyzes floor plan PDFs, detects automation opportunities, and produces annotated plans with pricing summaries. This repository contains the production-ready Flask application along with deployment scripts and configuration helpers.

## 🚀 Quick Start

To run the application locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000` in your browser.

## Deployment

Render deployment scripts are provided for convenience:

```bash
chmod +x build.sh deploy.sh config_updater.py
git add .
git commit -m "Deploy Lock Zone AI"
git push origin main
```

See `DEPLOY_NOW.md` for the full deployment walkthrough.

## Contributing & Pull Request Workflow

When you are ready to share changes back to GitHub:

1. Create a feature branch and push your commits.
2. Open a pull request (PR) from that branch. Use the “Create pull request” button to draft the proposal.
3. The PR will not merge automatically—you or a teammate must review the diff, address any feedback, and then press “Merge” (or enable auto-merge after approvals).
4. Once merged, GitHub will automatically close the PR and update the default branch.

If you lack permissions to merge, request a reviewer with the appropriate rights.

## Live App

The latest production deployment is available at:

https://lockzone-ai-floorplan.onrender.com

## API Endpoints

### `POST /api/analyze`
Upload a floor plan PDF, select automation systems and tier, and receive summary metrics along with download links for an annotated floor plan and quote PDF.

### `GET /api/data`
Returns the current automation catalog, tiers, and pricing data that power the analyzer.

### `POST /api/data`
Submit a JSON object to extend or override automation types, tiers, and pricing. Incoming payloads are merged with safe defaults, so customisations persist without blocking future updates.

## Analysis Enhancements

- Sequential PDF page rendering with pdf2image/PyMuPDF fallbacks for large documents.
- Advanced contour, OCR, and line-segmentation pipelines to detect rooms, text, labels, and structural lines before placing automation points.

## Updating the Automation Data

Automation symbols, pricing, and tier multipliers live in `data/automation_data.json`. To teach the app new categories or pricing:

1. Fetch the existing configuration with `GET /api/data`.
2. Merge your updates locally (add symbols, change prices, introduce tiers, etc.).
3. POST the revised JSON back to `/api/data`.

To persist those settings in source control, commit the updated `data/automation_data.json` file after posting.

# Tim-1
# ClaimPilot AI — MAGNA Hackathon, Zadanie 7

**AI Asistent pre zákaznícke reklamácie** — dark futuristic web app that analyzes customer complaints, photographs, and PDF documents, identifies missing information, recommends next steps, and generates an **editable D1–D8 draft**.

## Files (only 3)

- `index.html` — responsive Slovak-language UI, CSS, and JavaScript
- `server.py` — Python standard-library web server and server-side OpenAI API proxy
- `README.md` — setup and project notes

No `npm install`, `pip install`, or build step required. Python **3.9+** is recommended.

## Run locally

1. Obtain an OpenAI API key with billing/credits enabled at https://platform.openai.com/api-keys.
2. Set it in your **terminal**, never in HTML or GitHub:

   **macOS / Linux:**
   ```bash
   export OPENAI_API_KEY="your_key_here"
   python3 server.py
   ```

   **Windows PowerShell:**
   ```powershell
   $env:OPENAI_API_KEY="your_key_here"
   py server.py
   ```

3. Open **http://127.0.0.1:8000** (not `file://`).
4. Click **Vložiť príklad** and **Analyze with AI**, or upload your own JPG/PNG/WEBP/PDF files.
5. Review/edit the 8D report, then export as `.txt`.

The default model is `gpt-4.1-mini` (supports image and PDF inputs via the Responses API). To change it, set `OPENAI_MODEL` to another compatible model.

## Upload to GitHub

```bash
git init
git add index.html server.py README.md
git commit -m "Initial ClaimPilot AI prototype"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/claimpilot-ai.git
git push -u origin main
```

Create an empty repository on GitHub before running `git remote add origin`. **Do not commit API keys, customer-sensitive data, or `.env` files.**

## Hosting

**GitHub Pages alone cannot run the Python backend.** Use GitHub to host the source code and deploy the app to a Python-capable hosting provider. Set the `OPENAI_API_KEY` environment variable in the provider's **secret/environment settings** and start the service with `python server.py`. For hosted deployment, set `HOST=0.0.0.0` and the provider-specified `PORT`. Configure HTTPS, authentication, rate limiting, and production-grade request controls before handling real company data.

## Privacy and safety

- API key is read only on the server from `OPENAI_API_KEY`; it is never embedded in frontend code.
- Browser uploads are forwarded to the OpenAI API for processing; the app does not persist them to disk or maintain a database.
- Max 4 files, max 5 MB per file; supported formats: JPEG, PNG, WEBP, PDF.
- The server checks file signatures and rejects cross-origin browser requests.
- The report is **a draft requiring human validation**. Suspected root causes are hypotheses, not confirmed findings. The app does not claim to have completed corrective actions.
- This is a **hackathon prototype, not a production-ready or compliance-certified system**. Avoid uploading real personal/customer data without authorization and an approved data-processing arrangement. Public deployment requires authentication, quotas/rate limits, TLS, and stronger operational security.
- API usage is billed by OpenAI according to your account and model.

## API

- `GET /api/health` — server and API-key configuration status
- `POST /api/analyze` — JSON `{ "description": "...", "files": [{ "name": "photo.jpg", "type": "image/jpeg", "data": "<base64>" }] }`

The server uses the OpenAI Responses API with structured JSON output. Analysis is in Slovak.

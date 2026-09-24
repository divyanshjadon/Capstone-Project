# Predictive Maintenance Dashboard (Frontend)

A real client of the backend API in this repo — it polls `http://localhost:8000`
for every number it shows. No data is generated in the browser.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Then open the URL it prints (usually http://localhost:5173).

Make sure the backend is running first (mosquitto + the 4 Python services +
`uvicorn app:app --port 8000`, from the repo root) — otherwise you'll see a
"Backend not reachable" screen, which is expected and by design.

## Changing the backend URL

If your API runs somewhere other than `http://localhost:8000`, edit
`API_BASE_URL` near the top of `src/Dashboard.jsx`.

## Notes

- Styling uses the Tailwind Play CDN (loaded in `index.html`) rather than a
  full Tailwind build — fine for a demo/dev setup, not recommended as-is for
  a production deployment.
- `npm run build` produces a static `dist/` folder if you want to host this
  separately from the dev server.

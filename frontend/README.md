# Dashboard

Vite + React + TypeScript UI for SavingsTracker. Production copies `dist/` into the FastAPI image.

```bash
npm ci
npm run dev
```

Proxies `/api`, `/login`, `/logout`, and `/auth` to `http://localhost:8000`. Sign in through that backend (Google OAuth). `npm run build` typechecks and emits `dist/`.

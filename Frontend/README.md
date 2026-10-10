# Sambhaash AI — Admin Dashboard

React 19 + Vite + TypeScript. Talks to the FastAPI backend in `../Backend`.

## Run

```bash
npm install
cp .env.example .env     # VITE_API_BASE_URL_DEV, Supabase keys
npm run dev              # http://localhost:5173
npm run build            # tsc -b && vite build
npx tsc -b               # type-check only
npm run lint
```

The backend must be running on the URL in `VITE_API_BASE_URL_DEV`. Sign-in is
Supabase Google OAuth; the access token is sent as a Bearer header by the axios
interceptor in `src/services/apiService.ts`.

## Pages

| Route | Page |
|---|---|
| `/dashboard/leads` | lead list, filters, CSV upload, bulk delete |
| `/dashboard/leads/:id` | call timeline with transcripts, score history, objections, notes |
| `/dashboard/rm` | HOT leads and RM assignment / conversion |
| `/dashboard/appendix` | knowledge-base documents |
| `/dashboard/analytics` | knowledge-base effectiveness |
| `/dashboard/queue` | job queue and dead-letter queue |
| `/dashboard/summaries` | generated call summaries |

## Notes

- Classification values are uppercase `HOT` / `WARM` / `COLD`, matching the backend.
- Saving lead notes needs the backend migration `002_lead_notes.sql`.
- The production build is a single ~1.1 MB chunk (over Vite's 500 kB warning).

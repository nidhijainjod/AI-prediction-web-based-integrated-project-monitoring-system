# Deploying ProjectAI (GitHub → Vercel) — 2026-09-12

Record of how this project was moved from GitHub to a live Vercel deployment,
and the steps to repeat this (for this project or a similar Flask app) from
scratch.

## Result

- **Live app**: https://projectai-gray.vercel.app/
- **Landing page** (public, live portfolio stats): https://projectai-gray.vercel.app/
- **Login**: https://projectai-gray.vercel.app/auth/login
- **Vercel project**: `alpha-squad5/projectai`
- **GitHub repo**: https://github.com/nidhijainjod/AI-prediction-web-based-integrated-project-monitoring-system
  (branch `AI_project`, which is the repo's default branch)
- Vercel is connected directly to that GitHub repo/branch, so **pushing to
  `AI_project` automatically triggers a new production deployment** — no
  manual redeploy needed going forward.

## The one architectural problem to know about

Vercel runs Python/Flask apps as **serverless functions**: a read-only
deployment bundle plus a writable `/tmp` that is **wiped on every cold
start** and not shared between concurrent instances. This app originally
used a local SQLite file (`instance/app.db`) and locally-trained model files
— neither can live in the read-only bundle, and neither would survive a
cold start if just pointed at `/tmp` as-is (you'd get an empty, unusable app
on every fresh instance).

**Fix applied in this repo** so the deployed link always works out of the box:

- `config.py` detects `VERCEL` (set automatically by Vercel) and redirects
  the SQLite path and the ML model artifacts path to `/tmp` when present.
- `app/seed_data.py` has `ensure_demo_data()` — an idempotent bootstrap
  (create tables, seed the 8 demo projects only if the users table is
  empty) called once from `create_app()` whenever `VERCEL` is set.
- `app/ml/predictor.py` already lazily trains the model on first prediction
  if the artifact files don't exist — so a cold start trains the two
  RandomForest models once and reuses them for the life of that instance.

**Trade-off**: this makes the live demo always work, but it is still a demo
data store — any project/task created on the live Vercel link may not
survive a cold start or the next deploy (a new instance re-seeds from
scratch). If you need real persistence for a live product, swap `config.py`'s
`SQLALCHEMY_DATABASE_URI` for a hosted Postgres connection string (e.g. Neon
or Supabase via the Vercel Marketplace) — no other code changes needed since
the app already reads `DATABASE_URL` from the environment.

## Files that make this deployable on Vercel

- `vercel.json` — tells Vercel to build `api/index.py` with `@vercel/python`
  and route every path to it.
- `api/index.py` — the serverless entrypoint; imports `create_app()` and
  exposes the resulting Flask `app` object (Vercel's Python builder
  auto-detects a WSGI `app` variable).
- `requirements.txt` — installed automatically during the Vercel build.
  (Note: `pandas` was removed from this file — it was an unused dependency
  that only added ~70MB of unnecessary bundle size.)

## Step-by-step: what was actually run

### 1. Prerequisite: code already pushed to GitHub

```powershell
cd C:\sihh
git init
git add -A
git commit -m "Initial commit"
git branch -M AI_project
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin AI_project
```

### 2. Get a Vercel access token

Vercel dashboard → `vercel.com/account/tokens` → **Create Token** → copy the
value (shown once).

### 3. Install/run the Vercel CLI and verify the token

No global install needed — `npx` runs it on demand:

```powershell
npx --yes vercel@latest whoami --token="<VERCEL_TOKEN>"
```

### 4. Deploy

Run from the project root (the same folder as `vercel.json`):

```powershell
npx --yes vercel@latest deploy --prod --yes --token="<VERCEL_TOKEN>"
```

What this does, in order:
1. Creates a new Vercel project for the current directory (or reuses the
   linked one if `.vercel/project.json` already exists).
2. Detects and connects the GitHub repository automatically (from the local
   git remote), so future pushes to the default branch auto-deploy.
3. Uploads the project, builds it with `@vercel/python` per `vercel.json`,
   and promotes the build straight to production (`--prod`).
4. Prints the production URL and a stable alias URL once ready.

### 5. Verify the deployment

```powershell
curl https://<your-app>.vercel.app/            # landing page, 200
curl https://<your-app>.vercel.app/auth/login  # login page, 200
```

Log in through the browser (not curl — Flask-WTF's CSRF protection requires
a same-origin `Referer` header on HTTPS POSTs, which browsers send
automatically but `curl` does not by default) with the seeded demo
credentials:

- Admin: `admin@projectai.com` / `Admin@123`
- Manager: `priya.manager@projectai.com` / `Manager@123`

## Redeploying after future code changes

Because the GitHub repo is connected to the Vercel project:

```powershell
git add -A
git commit -m "..."
git push origin AI_project
```

...is all that's needed — Vercel picks up the push and deploys automatically.
To deploy manually instead (e.g. from a different branch, or without
pushing to GitHub first), re-run the same command from step 4 above.

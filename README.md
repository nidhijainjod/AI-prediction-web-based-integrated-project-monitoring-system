# ProjectAI — AI-Powered Project Risk & Overrun Prediction Platform

A Flask + SQLite web app that lets **managers** create/manage projects and tasks, while an
**administrator** gets a single dashboard summarizing the entire portfolio — with an actual
trained machine-learning model predicting each project's final cost, schedule delay, and a
0–100 risk score, plus plain-English reasons and recommended actions.

## What's inside

- **Role-based access**: `admin` (read-only portfolio oversight + user management) and
  `manager` (full CRUD on their own projects/tasks).
- **Real ML model**: two `scikit-learn` RandomForestRegressors (cost overrun %, schedule delay
  in days) trained on a simulated historical dataset that encodes realistic PM dynamics
  (spend/schedule pace, blocked/overdue tasks → compounding risk). See `app/ml/`.
- **Explainable AI**: every prediction comes with the top 2–3 drivers of the risk score in
  plain English, plus a matching corrective recommendation — not a black box.
- **Admin dashboard**: aggregate stat cards (at-risk count, portfolio budget vs. predicted
  cost, avg overrun/delay), a risk-distribution chart, a planned-vs-predicted cost chart, and
  one compact, searchable/sortable/filterable table — not a raw dump of every project.
- **Manager workspace**: project cards, full project/task CRUD forms, and inline jQuery
  AJAX controls (task status dropdown + progress slider) that recompute the AI prediction
  live, without a page reload.
- **8 seeded demo projects** spanning Software, Infrastructure, Construction, Marketing and
  Research, deliberately tuned across Low/Medium/High/Critical risk so the dashboard shows a
  realistic spread out of the box.

## Tech stack

Flask 3, Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF), SQLite, scikit-learn, pandas,
Bootstrap 5, Chart.js, jQuery.

## Project structure

```
C:\sihh
├── app/
│   ├── admin/            # admin blueprint: dashboard, user CRUD, read-only project view
│   ├── auth/              # login/logout
│   ├── manager/           # manager blueprint: project + task CRUD
│   ├── api/                # jQuery AJAX endpoints (task quick-update, recalc prediction)
│   ├── ml/                 # feature engineering, model training, predictor
│   │   ├── features.py     # feature extraction from a Project's live state
│   │   ├── train.py        # generates synthetic historical data + trains the models
│   │   ├── predictor.py    # loads models, predicts, builds reasons/recommendations
│   │   └── artifacts/       # trained model files (.joblib) — created on first run
│   ├── models.py           # User, Project, Task, ProjectSnapshot (SQLAlchemy)
│   ├── templates/          # Jinja2 templates (Bootstrap 5)
│   └── static/              # css/js (jQuery + Chart.js glue code)
├── config.py
├── run.py                  # entry point (flask dev server)
├── seed.py                  # resets DB, creates users + 8 demo projects, trains model
├── requirements.txt
└── instance/                 # app.db (SQLite) is created here at runtime
```

## How to run it

Everything below assumes PowerShell in `C:\sihh` (already set up once, but repeated here for
future reference / another machine).

### 1. Create a virtual environment and install dependencies

```powershell
cd C:\sihh
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Seed the database (creates tables, trains the AI model, loads demo data)

```powershell
python seed.py
```

This drops and recreates all tables, trains the two prediction models from synthetic
historical data (saved under `app/ml/artifacts/`), then creates:

- 1 administrator + 5 managers
- 8 projects (with realistic tasks, costs, and 90+ days of cost/progress history each)
- A live AI prediction for every project

Re-run `python seed.py` any time to reset back to this clean demo state.

### 3. Run the app

```powershell
python run.py
```

Open **http://127.0.0.1:5000** in your browser.

### Demo logins

| Role          | Email                              | Password      |
|---------------|--------------------------------------|----------------|
| Administrator | admin@projectai.com                 | Admin@123      |
| Manager       | priya.manager@projectai.com         | Manager@123    |
| Manager       | rahul.manager@projectai.com         | Manager@123    |
| Manager       | sofia.manager@projectai.com         | Manager@123    |
| Manager       | james.manager@projectai.com         | Manager@123    |
| Manager       | kenji.manager@projectai.com         | Manager@123    |

## Using it

**As a manager**: log in, click *New Project*, fill in budget/dates/team size, then add
tasks. As soon as a project has at least one task, the AI prediction runs automatically
(and again every time you save a task or its progress). On the project page you can drag
the progress slider or change a task's status inline — the risk badge, predicted cost, and
"why this risk score" panel update immediately via AJAX.

**As the administrator**: log in to land on the Dashboard — the portfolio summary (not a
50-row wall of projects). Use the search box / risk / status filters and click any column
header to sort. Click *Details* on a project to see its full task list, a cost trend chart
(planned pace vs. actual), and the model's explanation + recommended actions. *Re-run AI
Prediction* forces a fresh recompute using the project's current data.

## How the AI prediction actually works

1. **Features** (`app/ml/features.py`): for a project's *current* stage, compute its spend
   pace vs. plan, schedule pace vs. plan, task completion/blocked/overdue ratios, team size,
   priority and category.
2. **Training** (`app/ml/train.py`): since there's no real "completed projects" history yet,
   a large synthetic population of plausible project stages is generated, with a simulated
   final outcome (cost overrun %, schedule delay) that encodes realistic relationships (e.g.
   spend running hot compounds into overrun; blocked/overdue tasks compound into delay) plus
   noise. Two `RandomForestRegressor` models are trained on this and saved to
   `app/ml/artifacts/`.
3. **Prediction** (`app/ml/predictor.py`): a project's live features are fed into both
   models to get a predicted final cost and delay. These combine into a 0–100 risk score
   (Low/Medium/High/Critical), and the features with the largest "unhealthy" deviation
   (weighted by the model's own feature importances) become the human-readable reasons,
   each mapped to a recommended corrective action.
4. **When it updates**: every time a task or project is saved (manager) or *Re-run AI
   Prediction* is clicked (admin/manager), `recompute_and_store()` re-scores the project and
   appends a snapshot for the trend chart.

**Swapping in real historical data later**: once you have actual completed-project outcomes,
replace `_simulate_dataset()` in `app/ml/train.py` with a query over your completed projects
(same feature columns, real `final_overrun_pct` / `final_delay_days` targets) and re-run
`python -m app.ml.train` — everything downstream (predictor, dashboard, explanations) stays
the same.

## Notes

- The dev server (`python run.py`) is for local use only; for production use a WSGI server
  (e.g. `waitress` on Windows) and switch `SQLALCHEMY_DATABASE_URI` to a real database if you
  outgrow SQLite.
- `SECRET_KEY` in `config.py` defaults to a dev value — set a real `SECRET_KEY` environment
  variable before deploying anywhere shared.

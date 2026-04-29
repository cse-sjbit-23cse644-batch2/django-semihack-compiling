# GradeDNA AI

A Django dashboard for academic analytics, redesigned with a modern sidebar-driven multi-page UI.

## Tech Stack
- **Backend**: Django 5 + SQLite
- **Frontend**: Vanilla HTML/CSS/JS, Chart.js (CDN), custom design system
- **Fonts**: Inter (Google Fonts) + JetBrains Mono

## Project Structure
```
gradedna/                 Django project (settings, urls)
analytics/                Main app: models, views, urls
templates/
  base.html               Shell: sidebar + topbar + page area
  partials/nav_item.html  Sidebar nav item with icons
  pages/                  One template per page (10 pages)
  report_template.html    PDF report template
static/
  css/app.css             Design system + page styles
  js/app.js               App-wide interactivity, DNA helix, gauge
```

## Pages
1. `/` — Dashboard (overview)
2. `/profile/` — My Profile
3. `/cgpa-planner/` — CGPA Planner (full What-If engine)
4. `/dna-profile/` — Academic DNA visualization
5. `/backlog-risk/` — Risk predictor + action plan
6. `/emotional-health/` — Wellness analysis
7. `/performance/` — Class comparison + Z-scores
8. `/what-if-compiler/` — Same as CGPA Planner (alias)
9. `/reports/` — CSV upload, dry-run, save, PDF download
10. `/settings/` — Account / Academic / Notifications / Appearance / Privacy

## Design Tokens (defined in `static/css/app.css`)
- Primary purple: `#6C3CE1`
- Page bg: `#F4F6FA`
- Card radius: 16px
- Button radius: 10px
- Pill radius: 999px

## Workflow
- `Start application`: `python manage.py runserver 0.0.0.0:5000 --noreload` (port 5000, webview)
- Restart the workflow after editing templates because `--noreload` is set.

## Data
- Mock data is provided in `analytics/views.py` (`DEFAULT_STUDENT`, `DEFAULT_SUBJECTS`).
- Real data flows in via `/reports/` CSV upload (uses existing `Student`, `Subject`, `ResultRecord` models).

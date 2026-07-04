# ClinGuard-AI

ClinGuard-AI is a governance and monitoring dashboard for clinical AI
systems. It gives compliance officers, ML engineers, and clinicians a single
place to review audit activity, track model health and drift, and monitor
training/validation pipeline runs.

This frontend is adapted from the [TailAdmin React](https://github.com/TailAdmin/free-react-tailwind-admin-dashboard)
dashboard template (MIT licensed — see `LICENSE.md`), which supplied the
base layout, theming, and reusable UI component library. Everything
domain-specific — routing, navigation, types, mock services, and the
Dashboard/Audit/Monitoring/Pipeline modules — has been rebuilt for
ClinGuard-AI.

Built on:

- React 19
- TypeScript
- Tailwind CSS v4
- React Router 7
- ApexCharts

## Status

This is a frontend-only build against mock data (see `src/services/`).
There is no backend yet — `src/api/client.ts` is a thin fetch wrapper ready
to swap the mocks for real API calls once one exists.

- **Dashboard** — live: KPIs, compliance trend, severity breakdown, recent
  audit activity, active alerts, and active pipeline runs.
- **Audit Log**, **Monitoring**, **Pipelines** — routed and scaffolded, full
  page builds are in progress.

## Getting Started

### Prerequisites

- Node.js 18.x or later (20.x+ recommended)

### Install & Run

```bash
npm install
npm run dev
```

```bash
npm run build    # type-check and production build
npm run lint      # eslint
npm run preview   # preview the production build locally
```

## Project Structure

```
src/
  api/          # fetch wrapper for the (future) backend
  services/     # mock data services, one per domain area
  types/        # shared domain types (Audit, Monitoring, Pipeline, Dashboard)
  utils/        # formatting helpers (dates, badge color mapping, etc.)
  layout/       # AppLayout, AppSidebar, AppHeader
  pages/
    Dashboard/
    Audit/
    Monitoring/
    Pipeline/
  components/
    dashboard/  # dashboard-specific widgets
    audit/
    monitoring/
    pipeline/
    cards/
    charts/
    tables/
    ui/         # reusable primitives (Badge, Button, Table, Modal, ...)
```

## License

Released under the MIT License — see `LICENSE.md`. The original TailAdmin
React template copyright notice is preserved there per its license terms.

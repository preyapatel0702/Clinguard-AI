# ClinGuard-AI

ClinGuard-AI is a clinical AI safety platform designed to detect hallucinations in AI-generated medical responses, validate clinical claims, assess clinical risk, and generate safe, explainable outputs using a multi-agent AI architecture.

---

# Repository Structure

```text
ClinGuard-AI/
│
├── backend/
│   ├── agents/
│   ├── api/
│   ├── explainability/
│   ├── knowledge/
│   ├── memory/
│   ├── middleware/
│   ├── ml/
│   ├── models/
│   ├── observability/
│   ├── orchestrator/
│   ├── repositories/
│   ├── routers/
│   ├── services/
│   ├── tests/
│   ├── tools/
│   └── main.py
│
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
│
├── .gitignore
├── README.md
└── .env.example
```

---

# Backend

- FastAPI
- Python
- Pydantic
- Multi-Agent Clinical AI Pipeline

### Pipeline

```text
InterceptorAgent
      ↓
DetectorAgent
      ↓
ValidatorAgent
      ↓
RiskAgent
      ↓
GeneratorAgent
      ↓
EvaluatorAgent
      ↓
MemoryAgent
      ↓
AlertAgent
```

---

# Frontend

- React
- TypeScript
- Vite
- Modern Dashboard UI
- Clinical Monitoring Dashboard
- Analytics & Explainability Views

---

# Current Status

- ✅ Phase 1–8B Completed
- ✅ Phase 9 – Explainability & Clinical Audit
- ✅ Phase 10 – Analytics & Monitoring
- ✅ Backend Deployed
- ✅Frontend Deployed

---

# Running the Backend

```bash
cd backend

pip install -r backend/requirements.txt

uvicorn backend.main:app --reload
```

Backend:

```
http://localhost:8000
```

Swagger API:

```
http://localhost:8000/docs
```

---

# Running the Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```
http://localhost:5173
```

---

# Deployment

### Backend

- Render

### Frontend

- Vercel

---

# Contributors

- **Preya Patel** — Backend Development & AI Systems
- **Riya Patel** — Frontend Development & UI

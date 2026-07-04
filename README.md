# 🩺 ClinGuard-AI

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
│   ├── data/
│   └── main.py
│
├── frontend/
│   ├── public/
│   ├── src/
│   ├── .env.example
│   ├── README.md
│   ├── LICENSE.md
│   ├── banner.png
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── eslint.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   └── index.html
│
├── .gitignore
├── README.md
└── LICENSE.md
```

---

# Backend

### Technologies

- FastAPI
- Python
- Pydantic
- Multi-Agent Clinical AI Pipeline

### AI Pipeline

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

### Core Features

- Medical Entity Extraction
- Hallucination Detection
- Clinical Claim Validation
- Clinical Risk Assessment
- Safe Response Generation
- Explainability Engine
- Clinical Audit Reports
- Analytics & Monitoring
- Session Memory
- Alert Generation
- Operational Dashboard APIs

---

# Frontend

### Technologies

- React
- TypeScript
- Vite
- Tailwind CSS
- Modern Dashboard UI

### Features

- Clinical Dashboard
- Risk Analytics
- Hallucination Monitoring
- Validation Analytics
- Agent Performance Dashboard
- System Health Monitoring
- Explainability Reports
- Audit Report Viewer

---

# Current Status

- ✅ Phase 1–8B Completed
- ✅ Phase 9 – Explainability & Clinical Audit
- ✅ Phase 10 – Analytics & Monitoring
- ✅ Backend Successfully Deployed on Render
- ✅Frontend Successfully Deployed on Vercel


---

# Running the Backend

```bash
cd backend

pip install -r backend/requirements.txt

uvicorn backend.main:app --reload
```

Backend URL

```
http://localhost:8000
```

Swagger Documentation

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

Frontend URL

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

# API Documentation

Swagger UI

```
/docs
```

---

# Contributors

- **Preya Patel** — Backend Development, AI Systems & Architecture
- **Riya Patel** — Frontend Development & UI/UX

---

# License

This project is licensed under the MIT License.

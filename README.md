# ClinGuard-AI

ClinGuard-AI is a clinical AI safety platform designed to detect hallucinations in AI-generated medical responses, validate clinical claims, assess risk, and generate safer, explainable outputs using a multi-agent architecture.

## Repository Structure

```
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
├── .gitignore
└── README.md
```

## Backend

- FastAPI
- Python
- Pydantic
- Multi-Agent Pipeline

Pipeline:

```
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

## Current Status

- ✅ Phase 1–8B Completed
- ✅ Phase 9 Explainability
- ✅ Phase 10 Analytics & Monitoring

## Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Contributors

- Preya Patel — Backend Development
- Riya Patel — Frontend Development

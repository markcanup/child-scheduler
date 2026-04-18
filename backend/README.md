# Backend

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run tests

```bash
PYTHONPATH=backend pytest -q backend/tests
```

## Milestone status

- Milestone 0: backend skeleton created
- Milestone 1: `POST /hubitat/action-catalog` implemented with tests
- Milestone 2: `GET /catalog` implemented with tests

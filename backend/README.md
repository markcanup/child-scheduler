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

## SAM deploy scaffold

`template.yaml` includes the current Lambda functions and HTTP API routes.

Example commands:

```bash
cd backend
sam build
sam deploy --guided
```

## Milestone status

- Milestone 0: backend skeleton created
- Milestone 1: `POST /hubitat/action-catalog` implemented with tests
- Milestone 2: `GET /catalog` implemented with tests
- Milestone 3: `GET /schedule/config` implemented with tests
- Milestone 4: compiler implemented with pure functions and tests
- Milestone 5: `PUT /schedule/config` implemented with tests

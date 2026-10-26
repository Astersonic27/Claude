# Kudos System

Internal-portal feature that lets employees give kudos to colleagues, with a public dashboard feed and admin moderation.
The full approved requirements, design and plan are in [SPECIFICATION.md](SPECIFICATION.md).

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                      # demo users, password: change-me-123  (admin user: "admin")
SECRET_KEY=change-me flask --app app run
```
Open http://127.0.0.1:5000 and sign in as `priya`, `liam`, `sofia` or `mohammed` (users) or `admin` (moderator).

## Tests
```bash
python -m unittest discover -s tests -t .
```

## Layout
```
app/            Flask app (auth, kudos API, moderation, templates, static)
tests/          Automated tests
seed.py         Demo data
SPECIFICATION.md
```

## Other work in this repository
- [`task3-orderbot-agent/`](task3-orderbot-agent/): OrderBot, an agentic AI design for automating hardware order processing (3-slide management deck, flowcharts, risk analysis).

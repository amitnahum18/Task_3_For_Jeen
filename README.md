# Task 3 – Multi-Agent Flow in Langflow (Jeen AI – Home Assignment)

A customer support system built on 3 Langflow Agents, with dynamic routing (not every message triggers every Agent/Tool) and two Tools: a parameterized SQL query tool against PostgreSQL, and email sending via Gmail.

## Table of Contents
- [Architecture](#architecture)
- [Repo Layout](#repo-layout)
- [Running Locally with Docker](#running-locally-with-docker)
- [Importing the Flow into Langflow](#importing-the-flow-into-langflow)
- [Global Variables in Langflow](#global-variables-in-langflow)
- [Environment Variables (.env)](#environment-variables-env)
- [Testing](#testing)
- [Error Handling](#error-handling)
- [Demo Video](#demo-video)

## Architecture

Three Agents, each with a clear, separate responsibility:

1. **Orchestrator Agent** (`BooleanRouterAgent`, see [custom_components/boolean_router_agent.py](custom_components/boolean_router_agent.py)) —
   Understands user intent and decides between exactly two response forms:
   - **FORM 2 – direct answer**: greetings, small talk, general questions about the system, prompt-injection attempts — answered directly, without touching Analysis/Response and without invoking any Tools.
   - **FORM 1 – ROUTE**: a real request (information, email, status) — forwards the context onward to the Analysis Agent.

   Implemented as a custom component that subclasses Langflow's built-in `AgentComponent` and adds a True/False branch (similar to an If/Else), so the decision itself is fully driven by the Agent's System Prompt (Agent Instructions), not hardcoded in the component.

2. **Analysis Agent** — retrieves information via the SQL Tool (read-only), identifies missing information (e.g. a request without a name/email/ticket number — in which case it does not query the DB at all), classifies urgency (Low/Med/High/Critical), and returns a structured output: `name/email | category & status | urgency | recommended action`.

3. **Response Agent** — composes the final customer-facing reply based on the Analysis output, and invokes the Gmail Tool **only** if the user explicitly asked to receive an email update.

**Tools:**
- **Support Requests Query Tool** (`SecureSupportQueryTool`, see [custom_components/sql_secure_query_tool.py](custom_components/sql_secure_query_tool.py)) — the agent never writes raw SQL; it passes structured filters (category / priority / status / customer_name / email) that are bound as query parameters, so there is no SQL-injection surface. The query is read-only (`postgresql_readonly=True` plus an unconditional rollback, even for SELECT).
- **Gmail Send Tool** (`GmailSendToolComponent`, see [custom_components/gmail_send_tool.py](custom_components/gmail_send_tool.py)) — sends a plain-text email via Gmail SMTP/STARTTLS, validating the recipient address and rejecting header-injection attempts (CR/LF in the address/subject).

## Repo Layout

| File/Folder | Description |
|---|---|
| [Task 3 Agents.json](<Task 3 Agents.json>) | The full Flow, exported from Langflow (import directly via Import) |
| [custom_components/](custom_components/) | The 3 custom components (Orchestrator router, SQL tool, Gmail tool) |
| [db/init/](db/init/) | Scripts that create `support_db` and seed the sample data, run automatically on the container's first startup |
| [docker-compose.yml](docker-compose.yml) | Langflow + Postgres for local development |
| [test_plan.md](test_plan.md) | Full test plan for each of the 3 Agents (input scenarios + expected behavior) |
| [run_tests.py](run_tests.py) | Runs the test scenarios against the live Flow via HTTP POST and prints/logs the results |

> The demo video (`Task_3.mp4`, ~137MB) is not included in this repo — see [Demo Video](#demo-video).

## Running Locally with Docker

```bash
cp .env.example .env   # fill in LANGFLOW_SUPERUSER / LANGFLOW_SUPERUSER_PASSWORD
docker-compose up -d
```

- Langflow: http://localhost:7860
- Postgres: localhost:5432 (user: `langflow`, password: `langflow`)

### Data persistence
Both volumes (`langflow_data`, `postgres_data`) persist data to disk. Stopping and restarting does not delete anything:
```bash
docker-compose stop
docker-compose start
```
Full reset (including data) only if you want to wipe everything:
```bash
docker-compose down -v
```

### Databases
The Postgres container holds two separate databases:
- `langflow_meta` — used by Langflow itself to store Flows and history.
- `support_db` — created automatically from [db/init/01_create_support_requests.sql](db/init/01_create_support_requests.sql) on first startup only, containing the `support_requests` table with the assignment's sample data (plus additional synthetic rows from [db/init/02_seed_fake_data.sql](db/init/02_seed_fake_data.sql) for aggregation/count test scenarios).

> The scripts in `db/init` run **only once**, when the Postgres volume is empty (first startup). To re-run them, first do `docker-compose down -v` (deletes the data) then `docker-compose up -d`.

## Importing the Flow into Langflow

1. Open Langflow (http://localhost:7860), create a new Flow → **Import** → select [`Task 3 Agents.json`](<Task 3 Agents.json>).
2. The two custom components (`SecureSupportQueryTool`, `GmailSendTool`) and the Orchestrator (`BooleanRouterAgent`) load automatically from [custom_components/](custom_components/) if that folder is set as Langflow's Custom Components Path (`LANGFLOW_COMPONENTS_PATH`), or you can copy the files manually into `~/.langflow/components`.
3. Set up the Global Variables (see next section) and bind them to the corresponding fields on the Tool components inside the Flow (SQL Tool / Gmail Tool).

## Global Variables in Langflow

Never put keys/passwords inside the Flow itself. Configure them via **Settings → Global Variables** in the Langflow UI, and point to them from the Agent/Tool components:

| Global Variable | Used by | Note |
|---|---|---|
| `SUPPORT_DB_HOST` | Support Requests Query Tool | e.g. `postgres` (from Docker's internal network) |
| `SUPPORT_DB_PORT` | Support Requests Query Tool | `5432` |
| `SUPPORT_DB_NAME` | Support Requests Query Tool | `support_db` |
| `SUPPORT_DB_USER` | Support Requests Query Tool | `langflow` |
| `SUPPORT_DB_PASSWORD` | Support Requests Query Tool | Secret — the DB password |
| `GMAIL_ADDRESS` | Gmail Send Tool | Sender address |
| `GMAIL_APP_PASSWORD` | Gmail Send Tool | Secret — 16-character App Password (requires 2-Step Verification on the Google account, not the regular account password) |

SQL Tool connection string from Langflow's internal Docker network:
```
postgresql://langflow:langflow@postgres:5432/support_db
```
To connect from your own machine (e.g. DBeaver/pgAdmin for manual inspection):
```
postgresql://langflow:langflow@localhost:5432/support_db
```

## Environment Variables (.env)

The `.env` file (not committed to Git — see [.env.example](.env.example)) is only used by the files in this repo (docker-compose and `run_tests.py`), and is entirely separate from Langflow's own Global Variables:

| Variable | Used for |
|---|---|
| `LANGFLOW_SUPERUSER` / `LANGFLOW_SUPERUSER_PASSWORD` | Langflow's admin user (`LANGFLOW_AUTO_LOGIN=false` in [docker-compose.yml](docker-compose.yml)) |
| `LANGFLOW_API_KEY` | Langflow API key, used by `run_tests.py` to run the tests against the Flow |
| `LANGFLOW_FLOW_URL` | The `/api/v1/run/<flow-id>` URL of the imported Flow |

## Testing

[test_plan.md](test_plan.md) details test scenarios for each of the three Agents (correct routing in the Orchestrator, correct Tool usage in Analysis, correct wording and Gmail invocation in Response), including edge cases: prompt injection, delete requests (the tool is read-only), customer not found, tool/connection failure, and multiple questions in a single message.

Running against the live Flow (Playground or HTTP POST):
```bash
python run_tests.py
```
Runs every scenario in [test_plan.md](test_plan.md) via HTTP POST against `LANGFLOW_FLOW_URL`, and writes the output to `results.md` (git-ignored — regenerate locally, it's not committed).

## Error Handling

- **Missing information** (Analysis) — if no name/email/ticket number can be identified, no DB query is made at all; the system asks for identifying details.
- **Request not found** — returns `Record Not Found` instead of fabricating data; urgency is classified as Med (not Low, since the risk is unknown).
- **Tool/DB connection error** — the SQL Tool returns an explicit error message (`Could not connect...` / `Query failed...`) that is distinguished from "not found"; handled separately ("Data Unavailable — Tool Error") and never presented as a fake success.
- **Update/delete requests** — the SQL Tool is strictly read-only (always rolls back, even after SELECT); any UPDATE/DELETE attempt is rejected at the tool level, and the agent reports that the change cannot be performed.
- **Email sending failure** — the Gmail Tool distinguishes between an invalid address, an authentication failure (SMTPAuthenticationError), a recipient refusal (SMTPRecipientsRefused), and a general connection failure; in every case it returns an explicit failure message, and the Response Agent never pretends the email was sent.
- **Unclear request / empty message** — the Orchestrator answers directly and asks for clarification, without routing onward and without invoking any Tools.
- **Prompt injection** — the Orchestrator detects it and refuses politely, without exposing the system prompt or internal tool names, and without routing onward.

## Demo Video

The video file (`Task_3.mp4`, 2–5 minutes, ~137MB) exceeds GitHub's file size limit (100MB per file) and is therefore not part of this repo. It is included separately in the submission (Google Drive) and demonstrates: the Flow and Agent roles, a 6–7 message conversation, how decisions are made and information moves between Agents, Tool invocation, the Langflow Trace (including Tool Input/Output), a Playground run, and a successful HTTP POST run.

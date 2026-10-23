# Payment RAG AI

Ask questions about payment code and business rules, review a pasted diff, or get an advisory review on a GitHub pull request.

## How it works

Streamlit sends a request to FastAPI. LangGraph retrieves the five most relevant text chunks from PostgreSQL/pgvector, then sends the evidence and question or diff to Groq or Ollama. The UI is optional: you can use FastAPI's `/docs` directly. GitHub Actions reviews PRs independently of the UI.

## Local setup (Windows PowerShell)

Install Git, Docker Desktop and Python 3.11 or 3.12. Start Docker Desktop. .NET 8 is optional unless you want to run the sample payment API.

```powershell
git clone https://github.com/rvnextgendev/paymentKnowledgeBasedTool.git
cd paymentKnowledgeBasedTool
docker compose up -d
docker compose ps
cd rag-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Copy `.env.example` only when `.env` does not already exist, to preserve your settings. On macOS/Linux, activate with `source .venv/bin/activate` and copy with `cp .env.example .env`. Never commit `.env` or share key values.

### Choose Ollama or Groq

For Ollama running in an existing Docker container named `ollama`, check the installed model:

```powershell
docker exec ollama ollama list
```

Use the exact installed model name in `rag-service/.env`. For example, if the list shows `llama3.2:latest`:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434
```

Alternatively, download the originally suggested model and set `OLLAMA_MODEL=llama3.2:3b`:

```powershell
docker exec ollama ollama pull llama3.2:3b
```

These Docker commands assume your Ollama container already exists and publishes port 11434. For a native Ollama installation, use `ollama list` and `ollama pull llama3.2:3b` instead. CPU inference can take time. No Groq key is required for Ollama.

For Groq, set these values in `.env`, replacing the placeholders:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your_private_key
GROQ_MODEL=exact_model_id_available_to_your_account
```

Select an available chat model in the Groq console. The code's default model may not be available to your account. Restart FastAPI after changing provider settings.

### Ollama: what this project uses

Ollama runs a language model locally and exposes an HTTP API. This project uses LangChain's `ChatOllama` integration in `rag-service/llm_provider.py` to generate chat answers and code reviews from retrieved evidence. It does not use Ollama for embeddings: `common.py` uses Hugging Face `all-MiniLM-L6-v2` for those, and PostgreSQL/pgvector stores them.

| Setting | Repository default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `groq` | Set to `ollama` to use your local Ollama server. |
| `OLLAMA_MODEL` | `llama3.2:3b` | Exact model tag requested from Ollama. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama address as seen by the FastAPI process. |

The earlier local model list showed `llama3.2:latest`; use that tag if it is still your installed model. A model in a screenshot is evidence of that local installation, not a change to the repository default. Inspect `ollama list` whenever switching machines. The UI shows the provider, not the effective model tag.

### Start Ollama with Docker (first-time setup)

Start Docker Desktop first. Check whether the container already exists:

```powershell
docker ps -a --filter "name=^/ollama$"
```

For a **new container**, run this once. The port is bound to your computer's loopback address for local use:

```powershell
docker run -d --name ollama -p 127.0.0.1:11434:11434 -v ollama:/root/.ollama ollama/ollama
docker exec ollama ollama pull llama3.2:3b
docker exec ollama ollama list
```

For an **existing container** named `ollama`, start it instead of repeating `docker run`:

```powershell
docker start ollama
docker exec ollama ollama list
```

Set `OLLAMA_MODEL` in `rag-service/.env` to the exact installed tag (`llama3.2:3b` for the download above, or `llama3.2:latest` if that is already installed), set `LLM_PROVIDER=ollama`, and use `OLLAMA_BASE_URL=http://localhost:11434`. Restart FastAPI after editing `.env`.

Check the container and server:

```powershell
docker ps --filter "name=^/ollama$"
docker logs --tail 50 ollama
Invoke-RestMethod -Uri 'http://localhost:11434/api/tags'
```

If the API is still starting, wait for the server to listen and retry the request. If port 11434 is already in use by native Ollama or another container, use that existing server or stop it before creating this container.

Stop and restart Ollama without deleting downloaded models:

```powershell
docker stop ollama
docker start ollama
```

The named volume retains downloaded models across container replacement. This basic command uses CPU; GPU setup depends on your hardware and Docker configuration. For a native Windows/macOS/Linux installation, install Ollama from https://ollama.com/download, then run `ollama pull llama3.2:3b`. If no server is running, start `ollama serve`; avoid launching another server if the desktop app already serves port 11434.

### Verify Ollama before using the UI

In PowerShell, list models through the same address that the host-based FastAPI app will use:

```powershell
Invoke-RestMethod -Uri 'http://localhost:11434/api/tags'
```

Test generation directly (replace the model tag if yours differs):

```powershell
$ollamaBody = @{
    model = 'llama3.2:3b'
    prompt = 'Explain why a payment amount must be greater than zero in one sentence.'
    stream = $false
} | ConvertTo-Json
$ollamaResult = Invoke-RestMethod -Method Post -Uri 'http://localhost:11434/api/generate' -ContentType 'application/json' -Body $ollamaBody
$ollamaResult.response
```

A generated response verifies Ollama itself. Next set `LLM_PROVIDER=ollama` and the matching `OLLAMA_MODEL` in `.env`, restart FastAPI, index documents, and test Ask AI or Analyze change. The model must already be downloaded; the Python application does not pull it automatically.

`localhost` works here because FastAPI runs directly on your computer and the Ollama container publishes port 11434. If you later containerize FastAPI, its `localhost` means that container: use the appropriate Docker service address, or `http://host.docker.internal:11434` for a host service on Docker Desktop. The current Compose file starts only PostgreSQL; it does not start Ollama or FastAPI.

To switch models, pull the desired model, copy its exact tag into `OLLAMA_MODEL`, and restart FastAPI. To switch back to Groq, set `LLM_PROVIDER=groq` and configure a valid Groq key/model. No Groq requests are made by the Ollama provider path. Keep port 11434 local; this demo assumes a trusted local Ollama endpoint.

### Index and start the application

From `rag-service`, with the virtual environment activated:

```powershell
python ingest.py
uvicorn app:app --reload --port 8000
```

In another terminal, activate the same environment and start the optional UI:

```powershell
cd rag-service
.\.venv\Scripts\Activate.ps1
streamlit run streamlit_app.py
```

Open http://localhost:8501 for the UI or http://localhost:8000/docs for direct API testing. Ask: `What happens if zero-value payments are allowed?`

For manual review, paste this diff in the Code Review tab:

```diff
- if (request.Amount <= 0)
+ if (request.Amount < 0)
```

In `/docs`, POST `/ask` accepts:

```json
{"question":"What happens if zero-value payments are allowed?"}
```

POST `/review` accepts:

```json
{"diff":"- if (request.Amount <= 0)\n+ if (request.Amount < 0)"}
```

## What ingest.py does

It reads `.cs`, `.md`, `.json`, `.yaml`, and `.yml` files under `sample-payment-api/` and `knowledge/`. It skips blank files, files larger than 2 MB, and dependency/build directories. It splits text into chunks of up to 1,200 characters with 200 characters of overlap.

The local Hugging Face model `sentence-transformers/all-MiniLM-L6-v2` embeds each chunk. PostgreSQL stores the chunk text, embedding vector, source path and starting character position. The default collection is `payment_code_chunks`; `.env` can override it through `COLLECTION_NAME` and select a database through `DATABASE_URL`.

**Each ingestion deletes and rebuilds the configured collection.** Run it after changing indexed files, while no live queries are running. It does not execute C# code, train the language model, or create payment transactions. The first run downloads embedding model files.

## Inspect PostgreSQL contents

From the project root, check database readiness and open SQL:

```powershell
docker compose exec db pg_isready -U rag -d payment_rag
docker compose exec db psql -U rag -d payment_rag
```

Inside `psql`:

```sql
-- Confirm the database and pgvector extension.
SELECT current_database();
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- List tables and inspect their columns.
\dt
\d langchain_pg_collection
\d langchain_pg_embedding

-- List knowledge collections and count chunks per collection.
SELECT uuid, name FROM langchain_pg_collection;
SELECT c.name, COUNT(e.id) AS chunks
FROM langchain_pg_collection c
LEFT JOIN langchain_pg_embedding e ON e.collection_id = c.uuid
GROUP BY c.uuid, c.name;

-- Read source metadata and a sample of indexed content.
SELECT id, LEFT(document, 500) AS content, cmetadata
FROM langchain_pg_embedding
LIMIT 5;

-- Inspect vectors without printing hundreds of numbers.
SELECT id, vector_dims(embedding) AS dimensions
FROM langchain_pg_embedding
LIMIT 5;

-- List indexed files and the number of chunks from each.
SELECT cmetadata->>'source' AS source, COUNT(*) AS chunks
FROM langchain_pg_embedding
GROUP BY cmetadata->>'source'
ORDER BY source;
```

For the current embedding model, expect 384 dimensions. Chunk counts depend on your files; ingestion prints the count for that run. If tables are missing or the collection is empty, check `DATABASE_URL` and run `python ingest.py`. Exit SQL with `\q`.

This is a knowledge database, not a payment transaction database. The local database uses the demo credentials in `docker-compose.yml`. The GitHub Actions database is separate and temporary. The current Compose file does not declare a named database volume; keep source documents so you can rebuild the index after container replacement.

## Debug UI requests in VS Code

Open the repository root in VS Code. Install Microsoft's Python and Python Debugger extensions. Use **Python: Select Interpreter** to select `rag-service/.venv/Scripts/python.exe` on Windows (or `.venv/bin/python` on macOS/Linux).

Create a `.vscode` folder at the repository root, then `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app:app", "--port", "8000"],
      "cwd": "${workspaceFolder}/rag-service",
      "envFile": "${workspaceFolder}/rag-service/.env",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

Stop any existing Uvicorn process first to release port 8000. Set a breakpoint inside `/ask` or `/review` in `rag-service/app.py`, or inside retrieval/review functions in `graph.py`. Press F5 to start Debug FastAPI, leave Streamlit running separately, and click Ask AI or Analyze change.

F10 steps over, F11 steps into, and F5 continues. Inspect Variables or hover over a value. Long pauses can exceed the UI request timeout. Request flow: `streamlit_app.py -> app.py -> graph.py -> PostgreSQL -> LLM -> UI`.

## GitHub Actions PR scenario

The workflow is `.github/workflows/payment-rag-review.yml`. It triggers on same-repository PR open, update and reopen events. A branch push with no PR does not trigger it. Fork PRs are skipped.

1. Open repository **Settings -> Secrets and variables -> Actions** and add a repository secret named exactly `GROQ_API_KEY`. Local `.env` values are not available to Actions. An environment secret also requires the workflow to select that environment, which this workflow does not do.
2. In the workflow's **Review PR and post comment** step, add an available model under `env`, alongside the existing key binding:

   ```yaml
   GROQ_MODEL: "exact_model_id_available_to_your_account"
   GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
   ```

   Replace the model placeholder. Both single and double quotes are valid YAML. Do not put your actual API key in YAML. Commit the configuration before testing.
3. In **Settings -> Actions -> General**, ensure Actions are permitted. The workflow requests `contents: read`, `pull-requests: write`, and `issues: write`. Organization policies may restrict these permissions. You do not need to enable automatic PR approval.
4. Create a test branch:

   ```powershell
   git checkout main
   git pull origin main
   git checkout -b test/zero-value-payment
   ```

5. In `sample-payment-api/Program.cs`, change `request.Amount <= 0` to `request.Amount < 0`. Then:

   ```powershell
   git add sample-payment-api/Program.cs
   git commit -m "Test review of zero-value payment change"
   git push -u origin test/zero-value-payment
   ```

6. Open a PR from that branch into `main`. Inspect **Actions -> Payment RAG AI PR Review -> review**, then the PR Conversation for the bot's comment. The expected finding is that zero-value payments become accepted, but model output is not a deterministic assertion.

The runner starts pgvector, indexes trusted base-branch files, retrieves the diff through GitHub's API, and posts or updates one advisory comment. It does not need your local UI, database, or Ollama. GitHub-hosted runners cannot reach Ollama at your laptop's localhost.

The workflow checks out the PR's base commit for application code. Put code fixes on `main`, then merge the updated base into the test branch and push to generate a fresh event:

```powershell
git checkout test/zero-value-payment
git fetch origin
git merge origin/main
git push
```

Re-running an old workflow uses its original event/ref; it may not pick up later workflow edits. A secret-only fix can be tested by re-running the failed job. Do not merge the intentionally faulty payment change; close the test PR afterward.

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| UI says API reachable but `/ask` or `/review` returns 500 | Read the traceback in the FastAPI terminal after clicking. API reachability alone does not validate retrieval or generation. |
| Ollama model not found | Run `docker exec ollama ollama list`; set `OLLAMA_MODEL` to the exact installed name and restart FastAPI. |
| Ollama is slow | CPU inference can be slow. Check the Ollama logs and allow time for model loading and generation. |
| HF Hub unauthenticated warning | Public embeddings can download anonymously with lower rate limits. No token is required if download succeeds; it is unrelated to Groq/Ollama credentials. Cached model files usually avoid repeat downloads. |
| PostgreSQL connection refused | Start Docker, run `docker compose up -d`, check readiness and port 5432 conflicts, and verify `DATABASE_URL`. |
| No indexed evidence | Run `python ingest.py` against the same database and collection as the API. |
| `langchain_pg_collection` already defined for MetaData | Pull the vector-store initialization fix from `main`, then fully restart FastAPI. The app reuses one store and serializes initialization. Do not delete database tables or add `extend_existing` as a workaround. |
| Actions: `Illegal header value b'Bearer '` | `GROQ_API_KEY` is empty in that run. Add the repository Actions secret with the exact name. |
| Groq: `404 model_not_found` | Select a model available to your account and set `GROQ_MODEL` in the workflow or local `.env`, as applicable. |
| Actions: 403 posting a PR comment | Ensure the executing workflow requests `pull-requests: write` and `issues: write`; inspect the run's token permissions and repository/organization restrictions. |
| No workflow run after pushing a branch | Open a same-repository PR. Check Actions is enabled; this workflow has no standalone push/manual trigger. |

## Limitations and safe use

Reviews are advisory: the workflow does not execute payment tests, approve PRs, merge, or enforce the suggested findings. Validate behavior separately. Groq receives retrieved source and diff text; use sanitized demo content and check provider policies before sending proprietary code. Retrieved code and diffs are untrusted data.

The workflow checks out the base branch and does not execute PR code. Large diffs are truncated at 18,000 characters; GitHub API pagination is capped at 500 changed files. Consider pinning Actions to full commit SHAs, branch protection and human review before production use.

Commands here describe the intended workflow. Full local execution and successful GitHub comment posting must be verified in your environment; documentation updates alone do not establish those checks passed.

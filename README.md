# Payment RAG AI: Chat + automatic GitHub PR review

## Flow
- `rag-service/ingest.py`: reads C# and Markdown, chunks (1200 characters, 200 overlap), embeds locally, stores in PostgreSQL pgvector.
- `rag-service/graph.py`: LangGraph conditional routing (`kind=chat` or `kind=pr`), retrieves top-5 chunks via LangChain PGVector, generates answer/review using Groq.
- `rag-service/app.py`: FastAPI `/ask` and `/review` endpoints.
- `rag-service/pr_review.py`: retrieves PR patches through GitHub API and creates/updates a PR conversation comment.
- `.github/workflows/payment-rag-review.yml`: automatically runs review on same-repo PR open/update/reopen.

## Local setup
1. Install Docker, Python 3.11+ and optionally .NET 8.
2. Run `docker compose up -d` from project root.
3. `cd rag-service` then `python -m venv .venv` and activate it (`.venv\\Scripts\\Activate.ps1` on PowerShell; `source .venv/bin/activate` on Linux/macOS).
4. `pip install -r requirements.txt`.
5. Copy `.env.example` to `.env`, set `GROQ_API_KEY`.
6. `python ingest.py` (downloads a local embedding model on first run).
7. `uvicorn app:app --reload --port 8000`; open `http://localhost:8000/docs`.
8. Ask `What happens if zero-value payments are allowed?` using POST `/ask`.
9. Test POST `/review` with `{ "diff": "- if (request.Amount <= 0)\\n+ if (request.Amount < 0)" }`.

## GitHub automatic PR demo
1. Push the complete project into a new private GitHub repository that you control. **Do not use real payment data or secrets.**
2. Under repository **Settings → Secrets and variables → Actions → New repository secret**, add `GROQ_API_KEY`.
3. Ensure Actions are enabled and GitHub Actions has permission to create issue comments (workflow declares `issues: write`; organization policies may restrict it).
4. Create a feature branch **in the same repository**. Modify `sample-payment-api/Program.cs`: change `request.Amount <= 0` to `request.Amount < 0`.
5. Commit and push the branch. Open a PR into the default branch.
6. Go to **Actions → Payment RAG AI PR Review** to inspect the run.
7. After completion, open the PR **Conversation** tab to read the AI review comment. Push another commit to trigger `synchronize` and update the existing bot comment.

## Security and limitations
- Only same-repository PRs are supported in this demo. Fork PRs are intentionally skipped to avoid exposing the Groq key to untrusted contributions.
- Workflow checks out the **base branch**, never executes untrusted PR code. PR diff is fetched as text through the GitHub API and treated as untrusted data.
- It does not run payment tests, merge, approve, or block PRs. Comments are advisory.
- A per-run ephemeral pgvector database is populated from base-branch code; not a persistent production vector store.
- Groq sees retrieved source and diff text. Use sanitized demo code and verify provider policies before sending proprietary code.
- Large diffs are truncated at 18,000 characters; some changes may not be reviewed. GitHub API pagination is capped at 500 changed files.
- This example has not been exercised against your GitHub account; test in a disposable private repo before production use.
- Consider pinning Actions to full commit SHAs, limiting permissions, enforcing protected branches and adding a human approval gate for production.

## One ZIP contents
- `sample-payment-api/` — runnable .NET 8 sample
- `knowledge/` — sample business rules and change history
- `rag-service/ingest.py` — chunking + embeddings + pgvector
- `rag-service/graph.py` — LangGraph conditional chat/PR routing
- `rag-service/app.py` — FastAPI `/ask` and `/review`
- `rag-service/pr_review.py` — GitHub API diff and PR comment
- `.github/workflows/payment-rag-review.yml` — GitHub Actions automation

## Demo readiness
Python files have been syntax-checked. End-to-end installation, Groq calls,
PostgreSQL indexing, and GitHub Actions execution require your own environment
and have not been validated here. `GROQ_API_KEY` is required. Do not commit `.env`.

## Streamlit dashboard + Groq / Ollama

Install Python dependencies using `pip install -r requirements.txt` inside `rag-service`.
Copy `.env.example` to `.env` and set `LLM_PROVIDER=groq` with `GROQ_API_KEY`, or use
`LLM_PROVIDER=ollama`, install Ollama, and run `ollama pull llama3.2:3b`.
Start PostgreSQL from the project root using `docker compose up -d`.
From `rag-service`, run `python ingest.py`, then in separate terminals:
```
uvicorn app:app --reload --port 8000
streamlit run streamlit_app.py
```
Open http://localhost:8501. The UI includes chat, manual diff review, and knowledge-base instructions.
Provider selection is via `.env` and requires restarting the API. GitHub Actions PR review
runs independently of the Streamlit interface and defaults to Groq unless configured otherwise.
GitHub-hosted runners cannot access Ollama running on your laptop at localhost.

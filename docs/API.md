# Payment RAG API

Default local base URL: `http://localhost:8000`.

Start from `rag-service` using the project environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --reload --port 8000
```

For VS Code on Windows, open the repository folder, select **Payment RAG: FastAPI** in **Run and Debug**, and press **F5**. The included launch configuration explicitly uses `rag-service/.venv/Scripts/python.exe` to avoid global-Python errors such as `No module named 'psycopg'`. Create the environment and install `rag-service/requirements.txt` using the README setup before debugging. Stop any existing API process on port 8000 first. Use **Payment RAG: Index knowledge** to run ingestion separately while API queries are stopped.

Prepare PostgreSQL, index the inputs with `python ingest.py` in the project environment, and configure Groq or Ollama as described in the [README](../README.md). This local demo has no API authentication configured.

## Interactive documentation

- [Swagger UI](http://localhost:8000/docs): expand an endpoint, click **Try it out**, edit the JSON, then click **Execute**.
- [ReDoc](http://localhost:8000/redoc): browse the API reference.
- [OpenAPI JSON](http://localhost:8000/openapi.json): machine-readable schema.

Send JSON requests with `Content-Type: application/json`. Both endpoints use the configured retrieval mode (`hybrid` by default) and return retrieved source references. The search mode is configured on the server, not per request.

## POST /ask

Ask a question about indexed payment code and business rules.

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `question` | string | Yes | 1–4,000 characters |

Request:

```json
{"question": "Explain PaymentRequest"}
```

Example HTTP 200 response (generated wording and source order can vary):

```json
{
  "answer": "PaymentRequest contains Amount and Currency. See sample-payment-api/Program.cs.",
  "sources": ["sample-payment-api/Program.cs char 0"]
}
```

PowerShell:

```powershell
$body = @{ question = 'Explain PaymentRequest' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8000/ask' -Method Post -ContentType 'application/json' -Body $body
```

## POST /review

Review a pasted diff against indexed evidence. This endpoint provides advice; it does not execute tests or approve merges.

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `diff` | string | Yes | 1–18,000 characters |

Request:

```json
{"diff": "- if (request.Amount <= 0)\n+ if (request.Amount < 0)"}
```

Example HTTP 200 response:

```json
{
  "review": "This change permits zero-value payments. Verify business approval and add regression tests against the indexed payment rules.",
  "sources": ["knowledge/payment-rules.md char 0", "sample-payment-api/Program.cs char 0"]
}
```

PowerShell:

```powershell
$diff = @'
- if (request.Amount <= 0)
+ if (request.Amount < 0)
'@
$body = @{ diff = $diff } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8000/review' -Method Post -ContentType 'application/json' -Body $body
```

## Responses and troubleshooting

| Status | Meaning | Action |
| --- | --- | --- |
| 200 | An answer or review was generated, or no indexed evidence was found | Inspect output and sources. An empty index returns a message asking you to run `ingest.py`, with empty sources. |
| 422 | Invalid request body, missing field, or length limit exceeded | Inspect the response's `detail` array and correct the request. |
| 500 | Unhandled retrieval, database, or model-provider failure | Read the FastAPI traceback; check PostgreSQL, ingestion, and provider settings. |

Source paths can use backslashes on Windows. Offsets identify the starting character of each retrieved chunk. Returned sources are retrieval results; verify that generated claims are supported by their content. If one retrieval branch fails, the other may still produce a response; warnings appear in server logs. API documentation being reachable does not confirm that the database or model service works. There is currently no `/health` endpoint.

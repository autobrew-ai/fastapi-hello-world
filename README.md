# fastapi-hello-world

A minimal FastAPI service used as the deployment target for the Autobrew
deployment engine's first live Railway deploy (M3).

## Endpoints
- `GET /` — hello message + whether a cache is configured
- `GET /healthz` — liveness check (dependency-free; always 200 once the app is up)
- `GET /cache/{key}` / `PUT /cache/{key}?value=…` — optional Redis demo, using the
  injected `REDIS_URL` (lazy connection — absent cache never blocks startup)

## Run locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# http://127.0.0.1:8000/healthz
```

## Deploy
The deployment engine provisions a Railway project + a Redis dependency, connects
this repo, injects `REDIS_URL` as a reference variable, and triggers the deploy.
The container start command comes from the `Procfile` (binds Railway's `$PORT`).

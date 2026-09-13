# Deploy / Shared Backend

One shared backend so the frontend dev and the demo hit the same URL - nobody spins up
their own. Postgres + backend + a Cloudflare tunnel, all in Docker.

## Run it

```bash
# from repo root
docker compose up -d --build
docker compose logs -f cloudflared      # find the public URL
```

`cloudflared` prints a public HTTPS URL like `https://<name>.trycloudflare.com`. That URL
proxies to the backend. Verify:

```bash
curl https://<name>.trycloudflare.com/api/v1/health
```

Services: `postgres` (5433 on host), `backend` (8000 on host + inside the tunnel),
`cloudflared` (the tunnel). No Redis - the backend doesn't use it.

## Point the frontend at it

- Local dev: `frontend/.env.local` -> `NEXT_PUBLIC_API_BASE=https://<name>.trycloudflare.com`
- Vercel: set `NEXT_PUBLIC_API_BASE` (and `NEXT_PUBLIC_USER_ID=demo-user`) in the project's
  Environment Variables, then deploy. `NEXT_PUBLIC_*` is inlined at build time, so changing
  it needs a redeploy.

## Stable named tunnel: https://revive-api.log0.in

`trycloudflare.com` URLs change every restart. For a stable URL (and Vercel) we use a named
tunnel on the `log0.in` Cloudflare domain via the **credentials-file** method - no Zero Trust /
credit card, just `cloudflared login` (once) + a credentials JSON. This is already set up; the
compose `cloudflared` service runs it from `backend/cloudflared/`.

Files: `backend/cloudflared/config.yml` (committed, the ingress) and
`backend/cloudflared/<tunnel-id>.json` (the secret credentials, gitignored).

**Single-level subdomain matters:** Cloudflare's free Universal SSL covers `log0.in` and
`*.log0.in` (one level) only. A deeper name like `api.revive.log0.in` fails TLS, so we use
`revive-api.log0.in`.

To recreate on another machine (or after deleting the tunnel):

```bash
cloudflared login                                  # browser auth, pick log0.in (no card)
cloudflared tunnel create revive                   # writes ~/.cloudflared/<id>.json
cloudflared tunnel route dns revive revive-api.log0.in
cp ~/.cloudflared/<id>.json backend/cloudflared/
# set tunnel id + credentials-file path in backend/cloudflared/config.yml
docker compose up -d cloudflared
curl https://revive-api.log0.in/api/v1/health
```

`https://revive-api.log0.in` is permanent - set it as `NEXT_PUBLIC_API_BASE` in Vercel and in
`frontend/.env.local`. To fall back to a quick tunnel, swap the compose `cloudflared` command
back to `tunnel --no-autoupdate --url http://backend:8000` and drop the volume.

## LLM latency vs determinism

With `REVIVE_USE_LLM=true` (default) each investigation makes a HuggingFace call (~10-15s) and
the cause is model-classified. For an instant, deterministic demo set `REVIVE_USE_LLM=false`
in `backend/.env` (the evidence heuristic classifies correctly on all seed scenarios) and
`docker compose up -d backend` to apply.

## Security note (hackathon)

The tunnel is public and unauthenticated (`X-User-Id` is a stub). Anyone with the URL can call
the API and save connections under `demo-user`. Fine for a short-lived demo; do NOT store real
customer tokens via `/connections` while the tunnel is public, and take the tunnel down after.

## env quoting

Docker Compose `env_file` passes values literally - keep `backend/.env` values UNQUOTED
(`HF_TOKEN=hf_...`, not `HF_TOKEN="hf_..."`), or the container reads the quotes as part of the value.

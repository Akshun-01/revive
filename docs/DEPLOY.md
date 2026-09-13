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

## Important: the quick-tunnel URL is ephemeral

`trycloudflare.com` URLs change every time `cloudflared` restarts. Fine for the frontend dev
and a live demo where the stack stays up. For a stable Vercel deployment, use a **named
tunnel** on your own Cloudflare domain instead:

```bash
cloudflared login                                  # browser auth, pick your domain
cloudflared tunnel create revive
cloudflared tunnel route dns revive api.<yourdomain>
# then run the tunnel with your credentials, or swap the compose cloudflared command to
# `tunnel run --token <token>` and map api.<yourdomain> -> http://backend:8000
```

That gives a permanent `https://api.<yourdomain>` you set once in Vercel.

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

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

## Stable named tunnel: https://api.revive.log0.in

`trycloudflare.com` URLs change every restart. For a stable URL (and Vercel), use a named
tunnel on your Cloudflare domain (`log0.in` is already active). Dashboard token method - no
cert files, works cleanly in Docker:

1. Cloudflare dashboard -> **Zero Trust** -> **Networks** -> **Tunnels** -> **Create a tunnel**
   -> **Cloudflared** -> name it `revive` -> **Save**.
2. On the connector screen, copy the **token** (the long string after `--token` in the shown
   `cloudflared ... run --token <TOKEN>` command). Ignore the install command itself.
3. Open the tunnel's **Public Hostname** tab -> **Add a public hostname**:
   - Subdomain: `api.revive`  ·  Domain: `log0.in`  ·  Path: empty
   - Service: **HTTP**  ·  URL: `backend:8000`   (cloudflared reaches the backend by its
     compose service name)
   - Save. Cloudflare auto-creates the `api.revive.log0.in` DNS record.
4. In the **repo-root** `.env` (copy from `.env.example`):
   ```
   CLOUDFLARE_TUNNEL_ARGS=run
   CLOUDFLARE_TUNNEL_TOKEN=<paste the token>
   ```
5. Bring the tunnel up:
   ```bash
   docker compose up -d cloudflared
   curl https://api.revive.log0.in/api/v1/health
   ```

Now `https://api.revive.log0.in` is permanent - set it once in Vercel and in
`frontend/.env.local`. To go back to a quick tunnel, blank both vars and re-up.

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

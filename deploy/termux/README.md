# Self-hosting on Termux: deploy notes

Runbook for the self-hosted home server (aarch64, Termux, Python 3.14, Node 24, PostgreSQL 18,
nginx on 127.0.0.1:8080, Cloudflare Tunnel). Public host: `undercut.maciejzielinski.dev`.
No Docker on the host.

**Every step marked [PRODUCTION] changes the running server and needs the owner's fresh approval
each time it is performed.** Steps without the mark are local (repo checkout, laptop build).

## Layout

| Part | Port / path | Supervisor (`~/services/`) | Start script |
|---|---|---|---|
| API (gunicorn, `config.wsgi`) | 127.0.0.1:8110 | `run-undercut-backend.sh` | `start-backend.sh` (runs `migrate --noinput` first) |
| Outbox worker | none | `run-undercut-worker.sh` | `start-worker.sh` |
| Scheduler | none | `run-undercut-scheduler.sh` | `start-scheduler.sh` |
| Next.js standalone server | 127.0.0.1:3110 | `run-undercut-frontend.sh` | `start-frontend.sh` |

- Checkout: `~/undercut`. Env file: `~/.config/undercut/env` (mode 600, from `env.example`, never committed).
- Assembled frontend build: `~/undercut/frontend-run` (`server.js`, `.next/static`, `public`).
- Logs: `~/services/logs/undercut-<name>.log`. Supervisors wait for PostgreSQL and restart the app after 5 s.
- nginx: `/api/`, `/admin/`, `/static/` go to 8110, everything else to 3110. No Redis: `CACHE_URL` stays unset
  (local-memory cache per process).
- Ports 8110 and 3110 were chosen without checking the host: confirm they are free first
  (`ss -ltn | grep -E ':(8110|3110)\b'`) and adjust `UNDERCUT_BACKEND_PORT`, `UNDERCUT_FRONTEND_PORT`,
  `API_INTERNAL_URL` and `nginx-server.conf` together if not.

## Prerequisites (Termux)

```sh
pkg install python clang make libpq postgresql nodejs-lts git
```

`psycopg[binary]` has no aarch64 Android wheel, so `install.sh` installs `psycopg[c]` (compiled against
the system libpq) instead. The dependency list is read from `backend/pyproject.toml`; nothing in the repo is changed.
If the build complains about the Android API level, `export ANDROID_API_LEVEL=36` and retry.

## First deploy

1. **Check the ports are free** (see above) and that the checkout is on the intended commit.
2. **Back up first** [PRODUCTION]: `mkdir -p ~/backups`, copy the current nginx config
   (`cp $PREFIX/etc/nginx/nginx.conf $PREFIX/etc/nginx/nginx.conf.bak-$(date +%Y%m%d)`), and the
   `~/.termux/boot/start-services` script. Also dump existing databases that share the instance if the
   owner wants a fresh point in time (`pg_dump -d <db> -Fc > ~/backups/<db>-<date>.dump`).
3. **Clone** [PRODUCTION]: `git clone <repo-url> ~/undercut && cd ~/undercut`
   (later: `git checkout <sha>`, never build from an unreviewed branch).
4. **Create the database role and database** [PRODUCTION] as the PostgreSQL superuser
   (unix socket, as the Termux user). Pick the password in your shell without echoing it into history:

   ```sh
   read -rs UNDERCUT_DB_PW && export UNDERCUT_DB_PW
   psql -d postgres <<SQL
   CREATE ROLE undercut LOGIN PASSWORD '${UNDERCUT_DB_PW}';
   CREATE DATABASE undercut OWNER undercut ENCODING 'UTF8';
   SQL
   psql -d undercut -c 'CREATE EXTENSION IF NOT EXISTS unaccent; CREATE EXTENSION IF NOT EXISTS pg_trgm;'
   unset UNDERCUT_DB_PW
   ```

   The backend relies on `unaccent` and `pg_trgm`; both ship with PostgreSQL contrib in the Termux package.
   If the migrations create the extensions themselves and the role lacks the right to do so, create them as above.
5. **Write the env file** [PRODUCTION]:
   `mkdir -p ~/.config/undercut && cp deploy/termux/env.example ~/.config/undercut/env && chmod 600 ~/.config/undercut/env`,
   then edit it: a long random `DJANGO_SECRET_KEY`, the DB password in `DATABASE_URL`. Do not paste its contents anywhere.
6. **Install the backend** [PRODUCTION]: `sh deploy/termux/install.sh` (creates `backend/.venv`, installs dependencies,
   runs `collectstatic`; compiles `psycopg-c`, takes a few minutes).
7. **Frontend build** (preferred: on the laptop; the standalone build is memory hungry on the server):

   ```sh
   cd frontend && npm ci && npm run build
   # assemble: standalone server + static assets + public
   mkdir -p /tmp/undercut-frontend/.next
   cp -R .next/standalone/. /tmp/undercut-frontend/
   cp -R .next/static /tmp/undercut-frontend/.next/
   cp -R public /tmp/undercut-frontend/
   tar czf - -C /tmp/undercut-frontend . | ssh -p 8022 <server> 'mkdir -p ~/undercut/frontend-run && tar xzf - -C ~/undercut/frontend-run'
   ```

   The `ssh` line is [PRODUCTION]. On the laptop the standalone output contains laptop-built `node_modules`; this is fine
   for pure JavaScript, but if a dependency ships native binaries (for example `sharp`), build on the server instead:
   `sh deploy/termux/install.sh frontend` (uses `NODE_OPTIONS=--max-old-space-size=1536`, one heavy job at a time).
   Before the first copy, back up any existing `~/undercut/frontend-run` (`cp -R` to `~/backups/undercut-frontend-<sha>`).
8. **Supervisors** [PRODUCTION]: copy `deploy/termux/services/run-undercut-*.sh` to `~/services/`, `chmod +x`.
   Add to `~/.termux/boot/start-services` (same style as the other services):

   ```sh
   nohup ~/services/run-undercut-backend.sh   >/dev/null 2>&1 &
   nohup ~/services/run-undercut-worker.sh    >/dev/null 2>&1 &
   nohup ~/services/run-undercut-scheduler.sh >/dev/null 2>&1 &
   nohup ~/services/run-undercut-frontend.sh  >/dev/null 2>&1 &
   ```

   To start them now without rebooting, run the same four lines once.
9. **nginx** [PRODUCTION]: back up `nginx.conf` (step 2). Copy `nginx-http.conf` and `nginx-server.conf` to
   `$PREFIX/etc/nginx/undercut-http.conf` and `undercut-server.conf`. Add `include undercut-http.conf;` once at http level
   and `include undercut-server.conf;` at http level after it (the file is a complete `server` block). Then
   `nginx -t` and, only if it passes, a single `nginx -s reload`. If the test fails, restore the backup; do not reload.
10. **Tunnel** [PRODUCTION]: in the Cloudflare dashboard (tunnel `home-server`, published application routes) add hostname
    `undercut`, domain `maciejzielinski.dev`, service `HTTP localhost:8080`.
11. **Create the admin user** [PRODUCTION]: load the env (`set -a; . ~/.config/undercut/env; set +a`) and run
    `backend/.venv/bin/python backend/manage.py createsuperuser` from `~/undercut/backend`.
12. **Verify**: `curl -s http://127.0.0.1:8110/api/health/` (loopback on the server), then
    `curl -sI -H 'Host: undercut.maciejzielinski.dev' http://127.0.0.1:8080/` and the public URL. Check the logs for errors.

## Update checklist

1. Tell the owner what changes (commit range, migrations, frontend rebuilt or not) and get approval [PRODUCTION].
2. **Back up first** [PRODUCTION]: `pg_dump -d undercut -Fc > ~/backups/undercut-<current-sha>.dump`, copy
   `~/undercut/frontend-run` to `~/backups/undercut-frontend-<current-sha>/`, and `nginx.conf` if nginx changes.
   Note the current sha (`git -C ~/undercut rev-parse --short HEAD`) as the rollback target.
3. `cd ~/undercut && git pull --ff-only` [PRODUCTION].
4. If `backend/pyproject.toml` changed: `sh deploy/termux/install.sh` (otherwise `collectstatic` still needs a re-run
   when static files changed). Migrations run on backend start.
5. If `frontend/` changed: build on the laptop and copy as in first deploy step 7.
6. If nginx snippets changed: copy, `nginx -t`, then one `nginx -s reload`.
7. **Restart by PID or port only. Never `pgrep -f` or `pkill -f`**, which can match other apps. Find the PID by the listening port
   or by an exact command line, and check it before sending TERM; the supervisor starts the process again after 5 s:

   ```sh
   ss -ltnp 2>/dev/null | grep ':8110 '     # gunicorn master PID for the API
   ss -ltnp 2>/dev/null | grep ':3110 '     # node PID for the frontend
   kill -TERM <pid>
   ```

   The worker and scheduler listen on no port: use `pgrep -af "[r]un_outbox_worker"` / `"[r]un_scheduler"`, confirm the
   output shows only the Undercut processes (path `~/undercut/backend`), then `kill -TERM <pid>`.
8. Verify as in first deploy step 12 and watch `~/services/logs/undercut-*.log` for a minute.

## Rollback

1. Stop nothing globally. `git -C ~/undercut checkout <previous-sha>` [PRODUCTION].
2. Reinstall dependencies if `pyproject.toml` differed (`sh deploy/termux/install.sh`), restore the frontend from
   `~/backups/undercut-frontend-<sha>/`, restore nginx from its `.bak` copy (then `nginx -t` and one reload).
3. Restart the processes by PID/port as above.
4. Migrations are not undone by a code rollback. If a migration must be reverted, restore the database from the dump taken in
   the backup step (`pg_restore -d undercut --clean --if-exists ~/backups/undercut-<sha>.dump`, with the API, worker and scheduler stopped by PID first).
   [PRODUCTION]

## Notes

- Scripts print no env values. Do not run `env` or `set -x` on the server with the env file loaded.
- Behind the proxy the API sees `127.0.0.1` as client address; nginx rate limits key on `CF-Connecting-IP`
  and pass it as `X-Forwarded-For`.
- Backups: `pg_dump -d undercut -Fc > ~/backups/undercut.dump`.

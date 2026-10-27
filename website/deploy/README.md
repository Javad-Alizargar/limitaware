# LimitAware website deployment

Target hostname: `https://wqp.statwhy.com` (DNS verified to `199.192.22.106` on 2026-10-26).
The server currently returns nginx 404/403 default responses; deployment is not yet performed.

## Required decisions (not inferred)
- SSH alias or `user@host` and key file
- deployment directory (e.g. `/opt/limitaware`)
- service user and process manager (systemd assumed)
- whether an existing nginx site/certificate must be preserved

## Topology to establish before changes
1. Does the SSH connection land on the server that owns 199.192.22.106, or on a jump host?
2. Which nginx server block currently serves `wqp.statwhy.com` (if any)?
3. Which TLS certificate covers the hostname?

## Suggested layout
```
<DEPLOY_DIR>/
  venv/                  # python3 -m venv; pip install .
  website/               # app.py, templates/, static/, config.json
  package/               # extracted LimitAware release
  releases/<date>/       # immutable copies
  current -> releases/<date>
```

## Procedure (after SSH details are confirmed)
1. Back up the current nginx site file, certificate paths and any existing service.
2. Upload a release archive; verify its SHA-256.
3. Create the venv and install the package and `website/requirements.txt`.
4. Install the systemd unit from `limitaware.service` (replace placeholders).
5. Add the nginx server block from `nginx.conf` (replace placeholders); obtain/renew TLS.
6. `systemctl daemon-reload && systemctl enable --now limitaware`.
7. `nginx -t && systemctl reload nginx`.
8. Verify `/`, `/docs`, `/app` sample analysis, invalid-input error, ZIP contents, version, and restart survival.

## Rollback
- Stop `limitaware`; restore the previous `current` symlink and nginx site file; `nginx -t && systemctl reload nginx`; restart the previous service.
- Do not delete unrelated sites or certificates.

## Security
- Bind gunicorn to 127.0.0.1; expose only nginx.
- Do not run Flask's development server.
- 2 MB upload limit, CSV parsing only, no execution, temporary directories deleted per request, in-memory download links expire after 10 minutes.

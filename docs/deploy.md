# Deploying kvaek.com

One server, Docker Compose, Caddy terminates HTTPS (certificates are automatic
via Let's Encrypt once DNS points at the server).

## One-time setup

**1. Server** — Hetzner Cloud (Falkenstein/EU), smallest shared instance is
plenty (CX22). Ubuntu 24.04, then:

```bash
curl -fsSL https://get.docker.com | sh
```

**2. DNS** — at the registrar for kvaek.com:

| Type  | Name | Value            |
|-------|------|------------------|
| A     | @    | <server IP>      |
| CNAME | www  | kvaek.com        |

**3. Email (Resend)** — create an account at resend.com, add domain
`kvaek.com`, add the DNS records they show (SPF + DKIM, also at the
registrar), wait for verification, create an API key.

**4. Code onto the server** — push this repo to a private GitHub repo and
`git clone` it on the server (or `rsync` the directory).

**5. Configure** — on the server, in the repo directory:

```bash
cp .env.prod.example .env.prod
# fill in: DJANGO_SECRET_KEY (openssl rand -base64 48),
#          POSTGRES_PASSWORD (openssl rand -hex 24),
#          EMAIL_HOST_PASSWORD (the Resend API key)
```

**6. Start**

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

**7. First-run housekeeping**

```bash
alias dcp='docker compose -f docker-compose.prod.yml --env-file .env.prod'
dcp exec backend python manage.py createsuperuser
dcp exec backend python manage.py shell -c "
from django.contrib.sites.models import Site
Site.objects.filter(id=1).update(domain='kvaek.com', name='Kvæk')"
dcp exec backend python manage.py shell -c "
from accounts.models import InviteCode
[InviteCode.objects.get_or_create(code=f'BETA-{i:03d}') for i in range(1, 21)]"
```

Optionally seed demo creators: `dcp exec backend python manage.py seed_creators --count 25`
(remove before real launch: `--clear`).

## Updating

```bash
git pull && dcp up -d --build
```

Migrations and collectstatic run automatically on backend start.

## Backups

Until a managed solution exists, a nightly dump (run from cron on the server):

```bash
dcp exec -T db pg_dump -U app app | gzip > /root/backups/kvaek-$(date +%F).sql.gz
```

Media lives in the `media` and `private_media` Docker volumes — include
`/var/lib/docker/volumes/kvaek_media` and `kvaek_private_media` in any backup.

## Notes

- Mollie: with a real `MOLLIE_API_KEY` set, webhooks work automatically in
  production (`BACKEND_URL=https://kvaek.com` is publicly reachable).
- The admin lives at https://kvaek.com/admin — staff accounts only.
- Verification evidence is never web-served; admins access it through the
  authenticated `/staff/...` link in the admin.

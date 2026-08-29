# Supabase + Edge Functions on Railway

A community Railway adapter for the official Supabase self-hosted Docker snapshot `self-hosted/v0.8.0` at commit `241bb11c0627f2981746d37033f57dbfa81d29b0`.

## What deploys

| Service | Purpose | Persistence |
|---|---|---|
| gateway | Envoy API gateway and Basic Auth for Studio | none |
| db | Supabase Postgres 17 | Railway volume |
| auth | Email and OAuth authentication | Postgres |
| rest | PostgREST API | Postgres |
| realtime-dev | Database change subscriptions | Postgres |
| storage | Storage API | Railway S3 bucket |
| imgproxy | Image transformations | Railway S3 bucket |
| meta | Database metadata for Studio | Postgres |
| functions | Supabase Edge Runtime with the hello function | immutable image |
| studio | Supabase dashboard | none |
| pooler | Supavisor transaction pooler | Postgres |

Logflare and Vector are not included. Vector needs a Docker socket, which Railway does not expose. Railway service logs remain available.

## First deploy

1. Deploy the template and wait for Postgres initialization. The first boot normally takes several minutes.
2. Open the gateway domain. Read `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` from the gateway service Variables tab.
3. In Studio, open Project Settings, then API to copy the project URL, anon key, and service-role key.
4. Create a table and test the REST API, Storage, Realtime, and `/functions/v1/hello` before adding production data.

No deploy form values are required. One generated `JWT_SECRET` deterministically produces matching API keys inside Gateway, Storage, Studio, and Edge Runtime.

## Production auth setup

A fresh deploy uses email auto-confirm so signup works without a fake SMTP server. Before opening registration to users:

1. Add a real SMTP provider to the auth service.
2. Set `GOTRUE_MAILER_AUTOCONFIRM=false`.
3. Set `GOTRUE_SITE_URL` to your application URL.
4. Add application callback URLs to `GOTRUE_URI_ALLOW_LIST`.
5. Set `GOTRUE_DISABLE_SIGNUP=true` after creating the accounts you need if registration should be closed.

OAuth and SMS providers are optional and use the normal GoTrue environment variables from the Supabase self-hosting docs.

## Edge Functions

The upstream `hello` function is included. Railway cannot attach one writable volume to both Studio and Edge Runtime, so function code is immutable in both images.

To add a function:

1. Fork this repository.
2. Add `images/functions/functions/<name>/index.ts`.
3. Build a new tag with the included GitHub Actions workflow.
4. Point both Functions and Studio at that tag, then redeploy both services.

Studio can inspect the matching function tree, but it does not live-edit the running Functions service.

## Storage

Storage and imgproxy use the bundled Railway S3 bucket. Every template reference is keyed by the bucket name `supabase-storage`, never by a bucket UUID. Railway buckets use public networking and do not include automatic backups. Configure an external S3-compatible provider later if those limits do not fit your workload.

## Database access

The db service exposes direct Postgres on its Railway TCP proxy. The pooler service exposes Supavisor transaction pooling on port 6543. Find both generated domains and ports in Railway after deploy.

## Upgrades

Supabase self-hosted snapshots are tested as a set. Do not bump one service image independently unless Supabase documents that combination as compatible.

To update this adapter:

1. Change `UPSTREAM_VERSION` to a released self-hosted tag and commit.
2. Replace vendored files from that exact commit.
3. Refresh `test/upstream.sha256`.
4. Update every image tag in `template.json`.
5. Run `test/all.sh`, build all wrappers, and verify a fresh template deploy.

## Audit trail

- `template.json` is the complete Railway build sheet and explains every deviation.
- `test/upstream.sha256` proves which files match upstream byte-for-byte.
- `test/gateway-health.py` proves `/healthz` is the only route change.
- `test/gateway-networking.py` proves the CDS changes only Docker hostnames to Railway private DNS.
- `boot/derive-keys.sh` is covered by fixed HS256 test vectors.

Supabase's vendored files are Apache-2.0 licensed. This adapter is also distributed under Apache-2.0.

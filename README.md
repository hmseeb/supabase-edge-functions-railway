# Supabase + Edge Functions on Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/supabase-edge-functions)

A community Railway adapter for the official Supabase self-hosted Docker snapshot `self-hosted/v0.8.0` at commit `241bb11c0627f2981746d37033f57dbfa81d29b0`.

## What deploys

| Service | Purpose | Persistence |
|---|---|---|
| gateway | Envoy API gateway and Basic Auth for Studio | none |
| db | Supabase Postgres 17 | Railway volume |
| auth | Email and OAuth authentication | Postgres |
| rest | PostgREST API | Postgres |
| realtime-dev | Database change subscriptions | Postgres |
| storage | Storage API | Railway volume |
| meta | Database metadata for Studio | Postgres |
| functions | Supabase Edge Runtime with the hello function | immutable image |
| studio | Supabase dashboard | none |
| pooler | Supavisor transaction pooler | Postgres |

Logflare and Vector are not included. Vector needs a Docker socket, which Railway does not expose. Railway service logs remain available.

imgproxy and image transformation are not included either. See the Storage section for why.

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

Storage keeps objects on its own Railway volume. Uploads, downloads, public and signed URLs, row-level security, and the S3 protocol endpoint all work.

Image transformation (`/storage/v1/render/image/...`) is not available. Supabase's file backend hands imgproxy `local://` paths, so both processes need one shared filesystem, and a Railway volume attaches to exactly one service. Railway's public API also cannot provision the S3 bucket that would remove that requirement: `bucketCreate` returns a bucket whose environment instance never exists, so every bucket reference resolves to an empty string.

To enable transformations, point Storage at an external S3-compatible provider and add an imgproxy service:

1. On `storage`, set `STORAGE_BACKEND=s3`, `GLOBAL_S3_BUCKET`, `GLOBAL_S3_ENDPOINT`, `GLOBAL_S3_PROTOCOL`, `GLOBAL_S3_FORCE_PATH_STYLE=true`, `REGION`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`.
2. Add a `darthsim/imgproxy:v3.30.1` service with `IMGPROXY_BIND=:5001`, `IMGPROXY_USE_S3=true`, and the same credentials, endpoint, and region.
3. On `storage`, set `ENABLE_IMAGE_TRANSFORMATION=true` and `IMGPROXY_URL=http://imgproxy.railway.internal:5001`.
4. Redeploy both services. Existing objects stay on the volume; copy them to the bucket first if you need them.

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

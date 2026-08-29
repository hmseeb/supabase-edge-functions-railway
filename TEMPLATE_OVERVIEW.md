# Deploy and Host Supabase + Edge Functions on Railway

Supabase is an open source backend platform built around Postgres. This template deploys Studio, Auth, REST, Realtime, Storage, image transformations, Edge Functions, postgres-meta, Supavisor, and a persistent Supabase Postgres 17 database behind one Envoy gateway.

## About Hosting Supabase + Edge Functions

This template follows the official `self-hosted/v0.8.0` Docker snapshot and pins its tested service versions. Railway generates every database, dashboard, and JWT secret. Six thin wrapper images package the configuration files that Docker Compose normally bind-mounts. Matching anon and service-role API keys are derived automatically from one generated JWT secret, so the deploy form has no manual key-generation step.

Studio is available through the gateway and protected with generated HTTP Basic Auth. Storage uses a bundled Railway S3 bucket. Postgres data persists on a Railway volume. The direct database and Supavisor transaction pool both receive TCP endpoints.

## Common Use Cases

- Private Postgres backend with Auth, REST, Realtime, and Storage
- Development or staging Supabase environment under your Railway account
- Backend for web and mobile applications that need row-level security
- Edge Function experiments using the included Supabase Edge Runtime
- Migration target when managed Supabase does not fit data-location requirements

## Dependencies for Supabase + Edge Functions Hosting

### Deployment Dependencies

No external account or API key is required for the first deploy. Railway provisions one persistent volume and one S3-compatible bucket.

The full stack is resource intensive. Supabase documents 4 GB RAM and 2 CPU cores as the minimum for the complete self-hosted stack, with 8 GB RAM and 4 cores recommended for small to medium production workloads. Railway bills each running service and its storage usage.

### Implementation Details

After deploy, open the gateway domain with `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` from the gateway Variables tab. In Studio, open Project Settings, then API to copy the project URL, anon key, and service-role key.

The first deploy uses email auto-confirm so a real signup and login can be tested without a fake SMTP server. Before production, configure SMTP on Auth, set `GOTRUE_MAILER_AUTOCONFIRM=false`, set your application Site URL and allowed redirects, and close open signup if it is not required.

The included `/functions/v1/hello` function proves Edge Runtime is connected. Railway cannot share a writable volume between Studio and Edge Runtime, so function code is changed through the adapter repository. Fork it, add a function directory, build a new image tag, then redeploy both Functions and Studio.

Logflare and Vector are omitted. Vector requires access to the Docker socket, which Railway does not expose. Use Railway service logs instead.

Railway buckets use public networking and do not include automatic backups. Move Storage to another S3-compatible provider if you need private bucket networking or managed backups.

## Why Deploy Supabase + Edge Functions on Railway?

Railway provisions the complete multi-service backend, private networking, persistent Postgres storage, an S3 bucket, generated domains, and generated credentials from one template. This adapter removes the manual secret generator required by the largest existing Supabase template and includes Edge Functions that template omits.

#!/bin/sh
set -eu

/app/bin/migrate
/app/bin/supavisor eval "$(cat /etc/pooler/pooler.exs)"
exec /app/bin/server

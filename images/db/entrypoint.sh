#!/bin/sh
set -eu

data_root=/var/lib/postgresql/data
pgdata=${PGDATA:-$data_root/pgdata}
custom_data=$data_root/postgresql-custom

# Railway formats volume roots with lost+found; initdb requires an empty PGDATA.
rm -rf "$data_root/lost+found"
mkdir -p "$pgdata" "$custom_data"

# Supabase stores the pgsodium root key here. Keep it on the same Railway
# volume as PGDATA because a volume cannot attach to a second mount target.
if [ ! -e "$custom_data/.railway-initialized" ]; then
  cp -a /etc/postgresql-custom/. "$custom_data/" 2>/dev/null || true
  touch "$custom_data/.railway-initialized"
fi
chown -R postgres:postgres "$data_root"
rm -rf /etc/postgresql-custom
ln -s "$custom_data" /etc/postgresql-custom

export PGDATA="$pgdata"
exec docker-entrypoint.sh postgres \
  -c config_file=/etc/postgresql/postgresql.conf \
  -c data_directory="$pgdata" \
  -c log_min_messages=fatal

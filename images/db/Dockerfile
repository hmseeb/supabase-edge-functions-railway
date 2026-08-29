FROM supabase/postgres:17.6.1.136

COPY images/db/init-scripts/ /docker-entrypoint-initdb.d/init-scripts/
COPY images/db/migrations/ /docker-entrypoint-initdb.d/migrations/
COPY images/db/entrypoint.sh /usr/local/bin/railway-entrypoint.sh
RUN chmod +x /usr/local/bin/railway-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/railway-entrypoint.sh"]

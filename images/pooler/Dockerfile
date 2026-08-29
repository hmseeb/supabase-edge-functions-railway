FROM supabase/supavisor:2.9.5

USER root
COPY images/pooler/pooler.exs /etc/pooler/pooler.exs
COPY images/pooler/entrypoint.sh /usr/local/bin/railway-entrypoint.sh
RUN chmod +x /usr/local/bin/railway-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/railway-entrypoint.sh"]

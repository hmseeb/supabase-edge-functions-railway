FROM supabase/studio:2026.08.03-sha-022b374

USER root
RUN if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache openssl; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends openssl && \
      rm -rf /var/lib/apt/lists/*; \
    else \
      command -v openssl; \
    fi
COPY boot/derive-keys.sh /usr/local/bin/derive-keys.sh
COPY images/functions/functions/ /app/edge-functions/
RUN mkdir -p /app/snippets && chmod +x /usr/local/bin/derive-keys.sh

ENV ANON_KEY_VAR=SUPABASE_ANON_KEY \
    SERVICE_KEY_VAR=SUPABASE_SERVICE_KEY
ENTRYPOINT ["/usr/local/bin/derive-keys.sh", "docker-entrypoint.sh"]
CMD ["node", "apps/studio/server.js"]

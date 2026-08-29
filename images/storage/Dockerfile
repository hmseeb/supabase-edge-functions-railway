FROM supabase/storage-api:v1.60.4

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
RUN chmod +x /usr/local/bin/derive-keys.sh

ENV ANON_KEY_VAR=ANON_KEY \
    SERVICE_KEY_VAR=SERVICE_KEY
ENTRYPOINT ["/usr/local/bin/derive-keys.sh", "docker-entrypoint.sh"]
CMD ["node", "dist/start/server.js"]

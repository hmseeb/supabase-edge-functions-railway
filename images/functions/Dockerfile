FROM supabase/edge-runtime:v1.74.0

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
COPY images/functions/functions/ /home/deno/functions/
RUN chmod +x /usr/local/bin/derive-keys.sh

ENV ANON_KEY_VAR=SUPABASE_ANON_KEY \
    SERVICE_KEY_VAR=SUPABASE_SERVICE_ROLE_KEY
ENTRYPOINT ["/usr/local/bin/derive-keys.sh", "edge-runtime"]
CMD ["start", "--main-service", "/home/deno/functions/main", "-p", "9000"]

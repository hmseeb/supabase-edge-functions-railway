FROM supabase/edge-runtime:v1.74.0

# The pinned upstream image has no Config.User and runs as root.
RUN if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache openssl; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends openssl && \
      rm -rf /var/lib/apt/lists/*; \
    else \
      command -v openssl; \
    fi
COPY boot/derive-keys.sh /usr/local/bin/derive-keys.sh
COPY images/functions/entrypoint.sh /usr/local/bin/railway-entrypoint.sh
COPY images/functions/functions/ /home/deno/functions/
RUN chmod +x /usr/local/bin/derive-keys.sh /usr/local/bin/railway-entrypoint.sh

# Upstream provides no non-root account and writes its Deno cache as root.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["/usr/local/bin/railway-entrypoint.sh"]
# nosemgrep: dockerfile.security.missing-user.missing-user
CMD ["start", "--main-service", "/home/deno/functions/main", "-p", "9000"]

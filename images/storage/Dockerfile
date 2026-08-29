FROM supabase/storage-api:v1.60.4

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
COPY images/storage/entrypoint.sh /usr/local/bin/railway-entrypoint.sh
RUN chmod +x /usr/local/bin/derive-keys.sh /usr/local/bin/railway-entrypoint.sh

# Preserve the pinned upstream image's root runtime user.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["/usr/local/bin/railway-entrypoint.sh"]
# nosemgrep: dockerfile.security.missing-user.missing-user
CMD ["node", "dist/start/server.js"]

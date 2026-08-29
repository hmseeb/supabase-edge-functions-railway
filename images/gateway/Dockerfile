FROM envoyproxy/envoy:v1.39.0

COPY boot/derive-keys.sh /usr/local/bin/derive-keys.sh
COPY images/gateway/envoy.yaml /etc/envoy/envoy.yaml
COPY images/gateway/cds.yaml /etc/envoy/cds.yaml
COPY images/gateway/lds.template.yaml /etc/envoy/lds.template.yaml
COPY images/gateway/upstream-entrypoint.sh /usr/local/bin/supabase-envoy-entrypoint.sh
COPY images/gateway/entrypoint.sh /usr/local/bin/railway-entrypoint.sh
RUN chmod +x /usr/local/bin/derive-keys.sh \
    /usr/local/bin/supabase-envoy-entrypoint.sh \
    /usr/local/bin/railway-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/railway-entrypoint.sh"]
CMD []

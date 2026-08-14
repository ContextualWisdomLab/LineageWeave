FROM searxng/searxng@sha256:c2dc2d9e6b910653e8628361c23443222490e4cabbb9e02667b7847143db843b

COPY settings.yml /opt/lineageweave/settings.yml
COPY entrypoint.sh /usr/local/bin/lineageweave-searxng-entrypoint
RUN chmod 0755 /usr/local/bin/lineageweave-searxng-entrypoint

ENTRYPOINT ["/usr/local/bin/lineageweave-searxng-entrypoint"]

FROM python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d
WORKDIR /app
ENV LINEAGEWEAVE_COMPOSE_STANDIN=1
COPY http_standin.py /app/http_standin.py
RUN addgroup --system lineageweave \
    && adduser --system --ingroup lineageweave lineageweave \
    && chown -R lineageweave:lineageweave /app
USER lineageweave
CMD ["python", "/app/http_standin.py"]

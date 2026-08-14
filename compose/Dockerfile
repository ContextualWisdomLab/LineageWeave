FROM python:3.13-alpine
WORKDIR /app
ENV LINEAGEWEAVE_COMPOSE_STANDIN=1
COPY http_standin.py /app/http_standin.py
RUN addgroup --system lineageweave \
    && adduser --system --ingroup lineageweave lineageweave \
    && chown -R lineageweave:lineageweave /app
USER lineageweave
CMD ["python", "/app/http_standin.py"]

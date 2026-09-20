FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AEGIS_ENVIRONMENT=container AEGIS_DB_PATH=/var/lib/aegis/aegis.db
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && mkdir -p /var/lib/aegis && chown -R 10001:10001 /var/lib/aegis
EXPOSE 8000
USER 10001
CMD ["uvicorn", "aegis_forge.api:app", "--host", "0.0.0.0", "--port", "8000"]

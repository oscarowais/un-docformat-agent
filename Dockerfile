# UN DocFormat Agent — containerized app (hard submission requirement)
# Build:  docker build -t un-docformat-agent .
# Run:    docker run -p 8000:8000 --env-file .env un-docformat-agent
#         (omit --env-file to run rules-engine-only mode; AI fix stays disabled)
FROM python:3.12-slim

WORKDIR /srv/app

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY webui/ webui/
COPY samples/ samples/
COPY docs/ docs/

EXPOSE 8000
CMD ["python", "-m", "app.server"]

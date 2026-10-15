FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=web /web/dist frontend/dist
RUN python -m legallens.evaluate >/dev/null
WORKDIR /app/backend
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "legallens.api:app", "--host", "0.0.0.0", "--port", "8000"]

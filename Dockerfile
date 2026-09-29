FROM node:22-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_URL=sqlite:////data/store.db \
    MEDIA_ROOT=/data/media

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /build/frontend/dist ./backend/app/frontend
COPY deploy/start.sh ./deploy/start.sh
RUN chmod +x ./deploy/start.sh && mkdir -p /data

WORKDIR /app/backend
EXPOSE 8000
CMD ["/app/deploy/start.sh"]
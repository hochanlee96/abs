# Monorepo Project

This project is a monorepo containing a Next.js web application and a FastAPI backend with MariaDB.

## Structure

```
repo/
  apps/
    api/    # FastAPI backend
    web/    # Next.js frontend
  infra/    # Infrastructure (Docker, Database)
```

## Getting Started

1.  Copy `.env.example` to `.env` (create one if needed in specific apps).
2.  Run `docker-compose up --build` from `repo/infra`.

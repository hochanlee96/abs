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

Here is how to set up and run the project locally.

### Prerequisites

- [Docker & Docker Compose](https://www.docker.com/products/docker-desktop/)
- [Node.js](https://nodejs.org/) (v18+)

### Environment Setup

The project comes with placeholder environment variables for easy setup.

1.  Copy `.env.example` to `.env` if you have specific secrets (optional for local dev).

### Running with Docker (Recommended for Backend)

You can run the Database and API using Docker, and run the Web App locally for faster implementation feedback.

1.  **Start Infrastructure**:

    ```bash
    cd infra
    docker-compose up --build
    ```

    _(If `docker-compose` fails, try `docker compose`)_

2.  **Start Web App**:
    Open a new terminal:
    ```bash
    cd apps/web
    npm install
    npm run dev
    ```
    Access the web app at [http://localhost:3000](http://localhost:3000).

### Troubleshooting

- **`winner_team_id` error**: Fixed in schema. If you see DB errors, run `docker-compose down -v` to reset the volume.
- **`docker-credential-desktop` error**: Open `~/.docker/config.json` and remove `credsStore`.

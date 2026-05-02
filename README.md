# Git Back Up

Git Back Up is a self-hosted tool designed to mirror and back up Git repositories across different services (e.g., GitHub, GitLab, Bitbucket). It provides a central dashboard to manage sync schedules, monitor job status, and configure webhooks for automated notifications.

## Features

- **Repository Mirroring**: Full mirroring of repositories, including all branches or specific selections.
- **Scheduled Syncing**: Configurable replication intervals (e.g., every 24 hours) to keep your backups up to date.
- **Manual Triggers**: Trigger synchronization jobs manually from the dashboard.
- **Authentication Support**: Support for both HTTP Tokens (OAuth) and SSH Keys for secure repository access.
- **Task Management**: Powered by [Procrastinate](https://procrastinate.readthedocs.io/) for robust background job processing.
- **Webhooks**: Notify external services about sync results (success/failure).
- **Security**: Built-in user authentication, session management, and encrypted storage for repository credentials.
- **Audit Logs**: Detailed logs for every sync job, including stdout and stderr output with sensitive information masked.

## Tech Stack

- **Backend**: [Litestar](https://litestar.dev/) (Python)
- **Database**: [SQLAlchemy](https://www.sqlalchemy.org/) with PostgreSQL (Async)
- **Background Jobs**: Procrastinate
- **Styling**: Tailwind CSS
- **Authentication**: Custom Session-based Auth with PBKDF2 hashing

## Prerequisites

- Python 3.11+
- PostgreSQL
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd git-back-up
```

### 2. Install Dependencies

Using `uv`:

```bash
uv sync
```

### 3. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .example.env .env
```

Edit the `.env` file and set the following:

- `DATABASE_URL`: Your PostgreSQL connection string (e.g., `postgresql+asyncpg://user:pass@localhost:5432/dbname`).
- `PG_CONNECTION_STRING`: Required by Procrastinate (e.g., `postgresql://user:pass@localhost:5432/dbname`).
- `ENCRYPTION_KEY`: A 32-byte base64-encoded key for credential encryption. You can generate one using:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `WEBHOOK_SECRET`: Secret used to sign webhook payloads.

### 4. Database Setup

The application automatically creates the necessary database tables on the first startup. Ensure your PostgreSQL server is running and the database specified in `DATABASE_URL` exists.

## Running the Project

### 1. Start the Web Server

```bash
uv run litestar run
```
The dashboard will be available at `http://localhost:8000`.

### 2. Start the Background Worker

In a separate terminal, run the Procrastinate worker to process synchronization jobs:

```bash
uv run procrastinate --app=workers.tasks.app worker
```

### 3. Start the Scheduler (Optional)

The scheduler automatically defers periodic sync jobs. It is imported in `main.py`, but if you want to run it independently or debug:

```bash
uv run procrastinate --app=workers.tasks.app health
```

## First Steps

1. **Initial Setup**: When you first access the application, you will be redirected to the `/register` page. Create the first user account.
2. **Add a Repository**: Navigate to "Repositories" and click "New Repository". Configure the source and target URLs and add any necessary credentials.
3. **Trigger a Sync**: Click the "Sync Now" button on the repository detail page to verify the configuration.

## License

[MIT](LICENSE)

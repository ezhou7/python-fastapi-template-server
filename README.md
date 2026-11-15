# FastAPI + Postgres Template Server

A barebones FastAPI + Postgres template server. The example domain is a blog. There's no frontend. The API has endpoints for posts only. Users, comments and tags exist in the database, ready for more endpoints later.

## Requirements

- Python 3.14
- [Poetry](https://python-poetry.org/) 2.x (it uses the `.venv` folder in the project root)
- Docker, for Postgres

## Quick start

```bash
make install   # install dependencies into .venv
make db-up     # start Postgres 17 on localhost:5432
make migrate   # create the tables
make seed      # add starter users, posts, tags and comments
make server    # run the API at http://localhost:8000 (auto-reloads)
```

Interactive API docs: http://localhost:8000/docs

## API

| Method | Path | Description |
|---|---|---|
| GET | `/posts?limit=20&offset=0` | List posts, newest first (`limit` 1–100) |
| GET | `/posts/{id}` | Get one post |
| POST | `/posts` | Create a post: `{"author_id", "title", "body", "tags": [...]}` |
| PATCH | `/posts/{id}` | Change any of `title`, `body`, `tags` (`tags` replaces the whole set) |
| DELETE | `/posts/{id}` | Delete a post, along with its comments and tag links |

- Only users with the role `admin` or `blogger` can author posts. Any other author gets a 422.
- Tag names are trimmed and lowercased. A tag that doesn't exist yet is created.
- Status codes: 201 for create, 204 for delete, 404 for an unknown post, 422 for invalid input.

Example (the seeded blogger is `bella`):

```bash
AUTHOR=$(docker compose exec -T db psql -U app -d app -tAc "select id from users where username='bella'")
curl -X POST localhost:8000/posts -H 'content-type: application/json' \
  -d "{\"author_id\": \"$AUTHOR\", \"title\": \"Hello\", \"body\": \"First post\", \"tags\": [\"intro\"]}"
```

## Database

| Table | What it holds |
|---|---|
| `users` | Everyone, bloggers included. `role` is one of `admin`, `blogger`, `poster` (comments only), `lurker` (reads only) |
| `posts` | Posts. `author_id` points to `users` |
| `comments` | Comments. `post_id` points to `posts` and `user_id` to `users` |
| `tags` | Each tag name, once |
| `tag_post` | Which post has which tag |

Deleting a user deletes their posts and comments. Deleting a post deletes its comments and `tag_post` rows. Tags themselves are kept.

## Configuration

Settings are read from environment variables, or from a `.env` file in the project root:

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://app:app@localhost:5432/app` |
| `DB_ECHO` | `false` (set `true` to log every SQL statement) |

## Changing the schema

1. Edit `api/models.py`.
2. `make migration msg="describe the change"` generates a file in `migrations/versions/`. Review it.
3. `make migrate` applies it.

## Tests

```bash
make test
```

This recreates a separate `app_test` database, migrates it, and runs pytest against it. Tests refuse to run against any database whose name doesn't end in `_test`.

## Make targets

| Target | Does |
|---|---|
| `install` | `poetry install` |
| `db-up` / `db-down` | Start / stop Postgres (data is kept in a Docker volume) |
| `migrate` | Apply migrations |
| `migration msg="..."` | Generate a migration from model changes |
| `seed` | Add starter data (does nothing if users already exist) |
| `server` | Migrate, then run the dev server |
| `test` | Run the tests against a fresh `app_test` database |

## Layout

```
api/
  main.py          FastAPI app
  config.py        settings
  db.py            engine and per-request session
  models.py        SQLAlchemy models (all 5 tables)
  schemas.py       request / response models for posts
  routers/posts.py the posts endpoints
  seed.py          starter data
migrations/        Alembic migrations
tests/             pytest suite
```

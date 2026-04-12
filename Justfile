default:
    @just --list

install:
    uv sync

m:
    uv run python manage.py migrate

mm:
    uv run python manage.py makemigrations

mma app:
    uv run python manage.py makemigrations {{app}}

serve:
    uv run python manage.py runserver

runws:
    uv run daphne -b 0.0.0.0 -p 8000 wordle.asgi:application

# Run all tests
test:
    uv run python manage.py test

# Run tests for specific app
test-app app:
    uv run python manage.py test {{app}}

# Run tests with verbose
test-app-verbose app:
    uv run python manage.py test {{app}} --verbosity=2

lint:
    uv run ruff check .

format:
    uv run black .

typecheck:
    uv run mypy .

createsuperuser:
    uv run python manage.py createsuperuser

# Clear all games (dev env)
clear-games:
    uv run python manage.py shell -c "from game.models import Game; Game.objects.all().delete(); print('All games deleted')"

reset-db:
    rm -f db.sqlite3
    uv run python manage.py migrate
    @echo "Database reset complete"

# Run Redis (for ws)
redis:
    docker run -p 6379:6379 redis:alpha

dev:
    just runws

# Add Docker Commands
dcb:
    docker compose build --pull

dcb-nocache:
    docker compose build --pull --no-cache

dcu:
    docker compose up -d --build

dcd:
    docker compose down

dcl:
    docker compose logs -f

dcmm:
    docker compose run --rm django-server uv run python manage.py makemigrations
    docker compose run --rm django-server uv run python manage.py migrate

daphne-log:
    uv run daphne --access-log - wordle.asgi:application

activate:
    source .venv/bin/activate

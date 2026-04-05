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
    uv run daphne -b 0.0.0.0 8000 wordle.asgi:application

# Run all tests
# -> Delete db.sqlite3 (used for testing env)
# -> Migrate using test settings
# -> Run Test
test:
    rm -f db.sqlite3
    uv run python manage.py migrate --setings=wordle.settings_test
    uv run pytest --ds=wordle.settings_test

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

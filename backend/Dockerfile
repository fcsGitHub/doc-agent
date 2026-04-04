FROM python:3.11-slim

WORKDIR /app/backend

COPY pyproject.toml .
RUN pip install --no-cache-dir $(python -c "\
import tomllib, pathlib; \
d = tomllib.loads(pathlib.Path('pyproject.toml').read_text()); \
deps = d['project']['dependencies'] + d['project'].get('optional-dependencies', {}).get('dev', []); \
print(' '.join(deps))")

COPY . .

# Run migrations, seed data, then start server
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]

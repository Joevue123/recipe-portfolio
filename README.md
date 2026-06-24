# Recipe ETL Portfolio

An end-to-end data engineering project that downloads 400k+ recipes from Hugging Face, loads them into PostgreSQL, and serves them through a REST API — all containerized with Docker.

## Stack

- **Python** — ETL pipeline with psycopg2 and tqdm
- **PostgreSQL 16** — normalized schema with full-text and trigram search indexes
- **Flask + Gunicorn** — REST API
- **Docker / Docker Compose** — containerized API + database

## Project Structure

```
recipe-portfolio/
├── api/
│   ├── app.py            # Flask REST API
│   ├── Dockerfile
│   └── requirements.txt
├── pipeline/
│   ├── download_dataset.py   # Downloads recipe data from Hugging Face
│   ├── etl.py                # Parses and loads JSONL into PostgreSQL
│   └── requirements.txt
├── schema/
│   └── schema.sql        # Tables, indexes, seed data
└── docker-compose.yml    # API + PostgreSQL stack
```

## Quick Start

### Run with Docker Compose

```bash
git clone https://github.com/Joevue123/recipe-portfolio.git
cd recipe-portfolio
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5433` with the schema applied automatically
- **API** on port `5000` backed by gunicorn

Then load the recipe data:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt

# Download ~400k recipes from Hugging Face
python pipeline/download_dataset.py --source recipenlg

# Load into the container database
DATABASE_URL=postgresql://recipe_user:recipe_pass@localhost:5433/kitchen_portfolio \
  python pipeline/etl.py --source recipenlg --file data/recipenlg.jsonl
```

### Run Locally (without Docker)

```bash
# Requires PostgreSQL running locally
createdb kitchen_portfolio
psql kitchen_portfolio -f schema/schema.sql

python -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt

python pipeline/download_dataset.py --source recipenlg

DATABASE_URL=postgresql://user:pass@localhost:5432/kitchen_portfolio \
  python pipeline/etl.py --source recipenlg --file data/recipenlg.jsonl

pip install -r api/requirements.txt
DATABASE_URL=postgresql://user:pass@localhost:5432/kitchen_portfolio \
  python api/app.py
```

## API Endpoints

### `GET /recipes`

Search and filter recipes.

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Filter by title (case-insensitive) |
| `cuisine` | string | Filter by cuisine name |
| `limit` | integer | Max results, default 20, max 100 |

```bash
curl "http://localhost:5000/recipes?search=margarita&limit=3"
```

### `GET /recipes/<id>`

Fetch a single recipe by UUID.

```bash
curl "http://localhost:5000/recipes/4346aef7-968d-4997-a2ce-d2c62e8ff1c1"
```

### `GET /recipes/random`

Return a random recipe.

```bash
curl "http://localhost:5000/recipes/random"
```

**Example response:**

```json
{
  "id": "4346aef7-968d-4997-a2ce-d2c62e8ff1c1",
  "title": "Avocado Margarita",
  "source": "recipenlg",
  "source_url": "The Ultimate Bar Book",
  "instructions": "Combine ingredients in a blender with 1/2 cup ice...",
  "ingredients": [
    "1 1/2 ounces silver tequila",
    "1/2 ounce Cointreau",
    "1 ounce fresh lime juice"
  ]
}
```

## Dataset

Recipes are sourced from [Zappandy/recipe_nlg](https://huggingface.co/datasets/Zappandy/recipe_nlg) on Hugging Face — a 400k-record subset of the [RecipeNLG](https://recipenlg.cs.put.poznan.pl/) corpus.

A smaller cocktail demo dataset (`--source cocktails`) is also available for quick testing.

## Schema

Key tables:

| Table | Description |
|-------|-------------|
| `recipes` | Core recipe data — title, instructions, source, nutrition fields |
| `recipe_ingredients` | Raw ingredient text with sort order |
| `cuisines` | Cuisine lookup |
| `import_runs` | Audit log for each ETL run |

Indexes include `pg_trgm` trigram search on `recipes.title` and a GIN index on the `recipe_search` tsvector for full-text search.

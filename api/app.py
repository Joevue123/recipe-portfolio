"""
Recipe REST API

Endpoints:
    GET /recipes?search=pasta&cuisine=italian&limit=20
    GET /recipes/<id>
    GET /recipes/random

Requires DATABASE_URL environment variable.
"""

import os

import psycopg2
import psycopg2.extras
from flask import Flask, g, jsonify, request

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        g.db.autocommit = True
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _fetch_ingredients(cur, recipe_ids):
    """Return {recipe_id: [raw_text, ...]} for a list of UUIDs."""
    cur.execute(
        """
        SELECT recipe_id::text, raw_text
        FROM recipe_ingredients
        WHERE recipe_id = ANY(%s::uuid[])
        ORDER BY recipe_id, sort_order
        """,
        (recipe_ids,),
    )
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["recipe_id"], []).append(row["raw_text"])
    return result


def _format_recipe(row, ingredients=None):
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "source": row["source"],
        "source_url": row["source_url"],
        "instructions": row["instructions"],
        "ingredients": ingredients or [],
    }


@app.get("/recipes")
def list_recipes():
    search = request.args.get("search", "").strip()
    cuisine = request.args.get("cuisine", "").strip()
    try:
        limit = min(int(request.args.get("limit", 20)), 100)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    cur = get_db().cursor()

    conditions = []
    params = []

    if search:
        conditions.append("r.title ILIKE %s")
        params.append(f"%{search}%")

    if cuisine:
        conditions.append("c.name ILIKE %s")
        params.append(f"%{cuisine}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    join = "LEFT JOIN cuisines c ON r.cuisine_id = c.id" if cuisine else ""

    cur.execute(
        f"""
        SELECT r.id, r.title, r.source, r.source_url, r.instructions
        FROM recipes r
        {join}
        {where}
        ORDER BY r.title
        LIMIT %s
        """,
        params + [limit],
    )
    rows = cur.fetchall()

    if not rows:
        return jsonify([])

    ids = [str(r["id"]) for r in rows]
    ing_map = _fetch_ingredients(cur, ids)

    return jsonify([_format_recipe(r, ing_map.get(str(r["id"]), [])) for r in rows])


@app.get("/recipes/random")
def random_recipe():
    cur = get_db().cursor()
    cur.execute(
        """
        SELECT id, title, source, source_url, instructions
        FROM recipes
        TABLESAMPLE SYSTEM (1)
        LIMIT 1
        """
    )
    row = cur.fetchone()

    if not row:
        cur.execute(
            "SELECT id, title, source, source_url, instructions FROM recipes ORDER BY RANDOM() LIMIT 1"
        )
        row = cur.fetchone()

    if not row:
        return jsonify({"error": "no recipes found"}), 404

    rid = str(row["id"])
    ing_map = _fetch_ingredients(cur, [rid])
    return jsonify(_format_recipe(row, ing_map.get(rid, [])))


@app.get("/recipes/<uuid:recipe_id>")
def get_recipe(recipe_id):
    cur = get_db().cursor()
    cur.execute(
        "SELECT id, title, source, source_url, instructions FROM recipes WHERE id = %s",
        (str(recipe_id),),
    )
    row = cur.fetchone()

    if not row:
        return jsonify({"error": "recipe not found"}), 404

    rid = str(row["id"])
    ing_map = _fetch_ingredients(cur, [rid])
    return jsonify(_format_recipe(row, ing_map.get(rid, [])))


if __name__ == "__main__":
    app.run(debug=True, port=5000)

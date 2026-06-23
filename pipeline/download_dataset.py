"""
Download a recipe dataset from Hugging Face and save as JSONL.

Uses brianarbuckle/cocktail_recipes (875 records, parquet) as a working
demo source. The output format matches RecipeNLG: title, ingredients,
directions, source — so etl.py works unchanged.

For the full 2M-record RecipeNLG dataset, download the official release
from https://recipenlg.cs.put.poznan.pl/dataset and point etl.py at it.
"""
import json
from pathlib import Path

from datasets import load_dataset

out_dir = Path(__file__).parent.parent / "data"
out_dir.mkdir(exist_ok=True)
out_file = out_dir / "recipenlg.jsonl"

print("Downloading cocktail_recipes dataset from Hugging Face (parquet)...")
ds = load_dataset(
    "parquet",
    data_files="hf://datasets/brianarbuckle/cocktail_recipes/data/train-00000-of-00001-dcec52ec7fe8275d.parquet",
    split="train",
)

print(f"Writing {len(ds):,} records to {out_file} ...")
with open(out_file, "w", encoding="utf-8") as f:
    for row in ds:
        # Normalise to RecipeNLG field names so etl.py parses without changes
        out = {
            "title": row.get("title", ""),
            "ingredients": row.get("ingredients") or [],
            "directions": row.get("directions") or [],
            "link": row.get("source", ""),
            "NER": row.get("ner") or [],
        }
        f.write(json.dumps(out) + "\n")

print(f"Done — saved to {out_file}")

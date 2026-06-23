"""
Download a recipe dataset from Hugging Face and save as JSONL.

Sources:
  recipenlg  — Zappandy/recipe_nlg (400k records, RecipeNLG train split)
  cocktails  — brianarbuckle/cocktail_recipes (875 records, quick demo)

Usage:
    python download_dataset.py --source recipenlg
    python download_dataset.py --source cocktails

Output format matches RecipeNLG: title, ingredients (list), directions (list),
link, NER — so etl.py works unchanged.
"""
import argparse
import json
from pathlib import Path

from datasets import load_dataset

OUT_DIR = Path(__file__).parent.parent / "data"
OUT_DIR.mkdir(exist_ok=True)

SEP = "<extra_id_99>"


def _split_field(val):
    """Split a SEP-delimited string into a cleaned list."""
    if isinstance(val, list):
        return [s.strip() for s in val if str(s).strip()]
    if isinstance(val, str):
        return [s.strip() for s in val.split(SEP) if s.strip()]
    return []


def download_recipenlg():
    out_file = OUT_DIR / "recipenlg.jsonl"
    print("Downloading Zappandy/recipe_nlg (train split) from Hugging Face...")
    ds = load_dataset("Zappandy/recipe_nlg", split="train", streaming=True)

    count = 0
    with open(out_file, "w", encoding="utf-8") as f:
        for row in ds:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            out = {
                "title": title,
                "ingredients": _split_field(row.get("ingredients")),
                "directions": _split_field(row.get("directions")),
                "link": "",
                "NER": _split_field(row.get("NER")),
            }
            f.write(json.dumps(out) + "\n")
            count += 1
            if count % 100_000 == 0:
                print(f"  {count:,} records written...")

    print(f"Done — {count:,} records saved to {out_file}")


def download_cocktails():
    out_file = OUT_DIR / "recipenlg.jsonl"
    print("Downloading brianarbuckle/cocktail_recipes from Hugging Face...")
    ds = load_dataset(
        "parquet",
        data_files="hf://datasets/brianarbuckle/cocktail_recipes/data/train-00000-of-00001-dcec52ec7fe8275d.parquet",
        split="train",
    )
    print(f"Writing {len(ds):,} records to {out_file} ...")
    with open(out_file, "w", encoding="utf-8") as f:
        for row in ds:
            out = {
                "title": row.get("title", ""),
                "ingredients": row.get("ingredients") or [],
                "directions": row.get("directions") or [],
                "link": row.get("source", ""),
                "NER": row.get("ner") or [],
            }
            f.write(json.dumps(out) + "\n")
    print(f"Done — saved to {out_file}")


def main():
    parser = argparse.ArgumentParser(description="Download recipe dataset")
    parser.add_argument(
        "--source",
        choices=["recipenlg", "cocktails"],
        default="recipenlg",
        help="Dataset to download (default: recipenlg)",
    )
    args = parser.parse_args()

    if args.source == "recipenlg":
        download_recipenlg()
    else:
        download_cocktails()


if __name__ == "__main__":
    main()

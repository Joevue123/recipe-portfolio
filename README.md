# Recipe Portfolio

A data pipeline project that ingests, transforms, and serves recipe data using Python, SQL/dbt, and cloud infrastructure.

## Project Structure

```
recipe-portfolio/
├── pipeline/       # Ingestion and transformation scripts
├── schema/         # Database schema definitions and dbt models
└── README.md
```

## Overview

This project builds an end-to-end data pipeline for recipe data:

1. **Ingest** — Extract recipe data from source(s) using Python
2. **Transform** — Clean and model the data with SQL/dbt
3. **Load** — Store processed data in cloud storage/warehouse (AWS/GCP/Azure)

## Getting Started

### Prerequisites

- Python 3.8+
- dbt Core
- Cloud CLI configured (AWS CLI / `gcloud` / Azure CLI)

### Setup

```bash
# Clone the repo
git clone <repo-url>
cd recipe-portfolio

# Install Python dependencies
pip install -r requirements.txt

# Configure dbt profile
cp schema/profiles.yml.example ~/.dbt/profiles.yml
# Edit ~/.dbt/profiles.yml with your connection details
```

### Running the Pipeline

```bash
# Run ingestion
python pipeline/ingest.py

# Run dbt transformations
cd schema
dbt run
dbt test
```

## Contributing

Open a PR or file an issue for bugs and feature requests.

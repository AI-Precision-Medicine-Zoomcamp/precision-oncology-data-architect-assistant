# Data Sources

The downloader uses `data/source_manifest.yaml`.

## Primary Collections

1. FHIR R4 Core
2. US Core
3. mCODE
4. Genomics Reporting IG

## Download Command

```bash
python -m src.ingestion.download_sources
```

## Collection-Specific Download

```bash
python -m src.ingestion.download_sources --collection mcode
python -m src.ingestion.download_sources --collection genomics_reporting
```

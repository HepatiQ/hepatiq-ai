# Data

This directory contains datasets, data processing utilities, and data management resources.

## Overview

The data module manages:
- Training and validation datasets
- Test data for model evaluation
- Data preprocessing and cleaning
- Data documentation and metadata
- Data privacy and security compliance

## Getting Started

### Data Organization

- Training data: Place in `training/` subdirectory
- Validation data: Place in `validation/` subdirectory
- Test data: Place in `test/` subdirectory
- Reference data: Place in `reference/` subdirectory

### Data Access

1. Ensure you have proper access permissions
2. Follow data privacy and security guidelines
3. Never commit sensitive data to version control
4. Use `.gitignore` to exclude data files (already configured)

## Key Responsibilities

- Organize and document datasets
- Maintain data quality standards
- Handle data preprocessing
- Ensure data privacy compliance (HIPAA, GDPR, etc.)
- Provide data access documentation

## Development Guidelines

- Document data source and collection methodology
- Include data schema and field descriptions
- Track data versions and update dates
- Maintain data lineage and transformations
- Create data validation checks

## Data Structure

Each dataset should include:
- **data.csv** or **data.parquet** - Main dataset file
- **metadata.json** - Schema and field descriptions
- **README.md** - Dataset documentation (optional but recommended)

Example metadata.json:
```json
{
  "dataset_name": "Patient Hepatic Data",
  "version": "1.0",
  "description": "...",
  "rows": 1000,
  "columns": [...],
  "collection_date": "2026-08-30"
}
```

## Security and Privacy

- **Never** commit actual patient data to version control
- Use `.gitkeep` for directory structure only
- Implement proper access controls
- Anonymize data according to HIPAA guidelines
- Document data handling procedures

## Related Components

- **ML** (`../ml/`) - Uses datasets for training
- **Validation** (`../validation/`) - Validates data quality
- **Backend** (`../backend/`) - Processes data from API requests

## Data Processing Workflow

1. Raw data acquisition → `raw/`
2. Data cleaning and preprocessing → `processed/`
3. Feature engineering → `features/`
4. Train/test split → `training/`, `test/`, `validation/`
5. Version control and documentation

## Contributing

When adding new data:
1. Follow the directory structure
2. Create comprehensive documentation
3. Include data validation checks
4. Verify privacy compliance
5. Update this README if adding new categories

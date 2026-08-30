# Machine Learning

This directory contains ML model training, development, and utilities for HepatiQ AI.

## Overview

The ML module handles:
- Model training and development
- Feature engineering
- Model evaluation and validation
- Inference pipeline setup
- Model versioning and management

## Files

- **train.py** - Model training script and training pipeline

## Getting Started

1. Ensure dependencies are installed from the root `requirements.txt`
2. Prepare your training data in the `../data/` directory
3. Run the training script:
   ```bash
   python ml/train.py
   ```
4. Trained models will be saved to `../models/`

## Key Responsibilities

- Develop and refine ML models
- Implement feature extraction and preprocessing
- Conduct model evaluation and hyperparameter tuning
- Create inference functions for backend integration
- Document model architecture and performance metrics

## Development Guidelines

- Use version control for model checkpoints
- Document all hyperparameters and training configurations
- Implement cross-validation for robust evaluation
- Track experiments and results systematically
- Follow best practices for data handling

## Related Components

- **Data** (`../data/`) - Training and validation datasets
- **Models** (`../models/`) - Trained model artifacts
- **Validation** (`../validation/`) - Model validation scripts
- **Backend** (`../backend/`) - Uses models for inference

## Model Management

- Save trained models in `../models/` with clear versioning
- Document model performance metrics
- Create model loading utilities for backend integration
- Maintain model compatibility across versions

## Contributing

When working on models:
1. Create a new branch for experimentation
2. Document your approach and findings
3. Validate against test sets
4. Update model documentation
5. Coordinate with validation team for deployment readiness

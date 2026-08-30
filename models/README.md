# Models

This directory stores trained ML models and model artifacts.

## Overview

The models directory contains:
- Trained model files (weights, checkpoints)
- Model metadata and performance metrics
- Model versioning information
- Model configuration files
- Pre-trained models for transfer learning

## Directory Structure

```
models/
├── model_v1/              # Model version 1
│   ├── model.pkl
│   ├── metadata.json
│   └── performance.json
├── model_v2/              # Model version 2
│   ├── model.pkl
│   ├── metadata.json
│   └── performance.json
└── current/               # Symlink to current production model
    └── model.pkl
```

## Getting Started

### Loading a Model

```python
import pickle

# Load a trained model
with open('models/model_v1/model.pkl', 'rb') as f:
    model = pickle.load(f)

# Use model for inference
predictions = model.predict(data)
```

### Model Naming Convention

Use semantic versioning for model releases:
- `model_v1.0` - First stable release
- `model_v1.1` - Bug fix or minor improvement
- `model_v2.0` - Major changes or architecture update

## Key Responsibilities

- Store trained model artifacts securely
- Maintain model versioning and history
- Document model performance and specifications
- Manage model lifecycle (development → staging → production)
- Coordinate with ML and backend teams

## Model Metadata

Each model version should include `metadata.json`:

```json
{
  "version": "1.0",
  "created_date": "2026-08-30",
  "algorithm": "Random Forest / Neural Network / etc.",
  "training_data": "Patient Hepatic Data v1.0",
  "training_samples": 5000,
  "features": [...],
  "input_shape": [1, 128],
  "output_shape": [1],
  "framework": "scikit-learn / TensorFlow / PyTorch",
  "compatible_backends": ["1.0", "1.1"],
  "notes": "..."
}
```

## Model Performance

Track performance metrics in `performance.json`:

```json
{
  "accuracy": 0.92,
  "precision": 0.89,
  "recall": 0.95,
  "f1_score": 0.92,
  "roc_auc": 0.96,
  "inference_time_ms": 45,
  "model_size_mb": 150
}
```

## Model Deployment

### Development Models
- Stored in version-specific directories
- Used for experimentation and testing

### Staging Models
- Validated and tested thoroughly
- Prepared for production deployment

### Production Models
- Symlinked as `current/`
- Monitored for performance
- Backed up regularly

## Best Practices

1. **Version Everything**: Always version models with metadata
2. **Document Performance**: Include accuracy and metrics
3. **Test Before Deploy**: Validate in staging first
4. **Keep History**: Maintain previous versions for rollback
5. **Track Dependencies**: Document required libraries and versions
6. **Security**: Protect model files with appropriate access controls

## Related Components

- **ML** (`../ml/`) - Creates and trains models
- **Backend** (`../backend/`) - Loads and uses models for inference
- **Validation** (`../validation/`) - Tests model performance

## Model Management Workflow

1. **Training** (ML team)
   - Train model using ML pipeline
   - Save to `models/model_vX.X/`

2. **Validation** (Validation team)
   - Test model performance
   - Generate performance metrics
   - Create validation report

3. **Review** (Team leads)
   - Review performance metrics
   - Approve for staging/production

4. **Deployment** (DevOps/Backend)
   - Deploy to staging environment
   - Run integration tests
   - Deploy to production if approved
   - Update `current/` symlink

5. **Monitoring** (All teams)
   - Monitor model performance
   - Alert on performance degradation
   - Plan for model retraining

## Contributing

When adding new models:
1. Create version-specific directory
2. Include metadata.json and performance.json
3. Update this README if adding new sections
4. Notify relevant teams of model availability
5. Ensure proper documentation for backend integration

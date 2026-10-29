# HepatiQ - Model Comparison

| Model | ROC-AUC (CV) | Precision | Recall | F1 Score | Brier Score |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Logistic Regression** (Selected) | 0.8800 | 0.7675 | 0.8105 | 0.7861 | 0.1363 |
| Random Forest | 0.8844 | 0.7235 | 0.8256 | 0.7694 | 0.1419 |
| XGBoost | 0.8706 | 0.7225 | 0.7880 | 0.7508 | 0.1528 |

*Logistic Regression selected for best calibration and clinical interpretability. See `models/candidates/training_metrics.json` for full details.*

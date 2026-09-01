#!/usr/bin/env python3
"""
Script to create all HepatiQ project issues using GitHub API
Run: python create_issues.py
"""

import requests
import json
from typing import Optional

GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  # Replace with your token
REPO = "HepatiQ/hepatiq-ai"
API_URL = "https://api.github.com"

issues_data = [
    {
        "title": "Load and preprocess Mayo Clinic PBC dataset",
        "body": """## Objective
Load the Mayo Clinic PBC dataset and implement comprehensive data preprocessing pipeline.

## Key Tasks
- [ ] Load dataset from data/ folder
- [ ] Handle missing values using IterativeImputer
- [ ] Implement data validation checks
- [ ] Document data schema and field descriptions
- [ ] Create metadata.json with dataset information
- [ ] Verify data quality and completeness

## Acceptance Criteria
- Dataset successfully loaded with no errors
- Missing values handled properly
- Data validation tests pass
- metadata.json created with accurate information
- Code is documented and follows PEP 8

## Related Components
- Data module: `data/`
- ML training: `ml/train.py`
- Validation: `validation/validate.py`

## Resources
- README.md (System Overview)
- data/README.md (Data handling guidelines)
- Pandas documentation: https://pandas.pydata.org/
- Scikit-learn IterativeImputer: https://scikit-learn.org/""",
        "assignees": [""],
        "labels": ["@Nirali-ML", "feature", "data-preparation"]
    },
    {
        "title": "Implement feature engineering pipeline",
        "body": """## Objective
Implement feature engineering for the 5 key lab values: Bilirubin, Albumin, Age, Prothrombin Time, and Platelets.

## Feature Details
The model uses these 5 features:
1. **Bilirubin** (mg/dL) - Liver function marker
2. **Albumin** (g/dL) - Protein level indicator
3. **Age** (years) - Patient age
4. **Prothrombin Time** (PT) - Blood clotting measure
5. **Platelets** (10^9/L) - Blood cell count

## Key Tasks
- [ ] Standardize features using StandardScaler
- [ ] Create feature interaction terms if needed
- [ ] Implement feature validation checks
- [ ] Document feature engineering approach
- [ ] Create feature documentation file
- [ ] Test feature pipeline with sample data

## Acceptance Criteria
- All 5 features properly scaled and validated
- Feature ranges documented
- Unit conversions handled correctly
- Code passes tests with sample data
- Documentation is comprehensive

## Depends On
- #1 (Load and preprocess dataset)

## Resources
- scikit-learn StandardScaler: https://scikit-learn.org/
- ml/README.md""",
        "assignees": [""],
        "labels": ["@Nirali-ML", "feature", "ml-pipeline"]
    },
    {
        "title": "Train ML models (Logistic Regression & Random Forest)",
        "body": """## Objective
Train and optimize Penalized Logistic Regression and Random Forest models on the preprocessed Mayo Clinic PBC dataset.

## Model Details
- **Penalized Logistic Regression**: L1/L2 regularization
- **Random Forest**: Multiple trees for ensemble learning
- **Cross-validation**: Stratified K-Fold (k=5)
- **Output**: Mortality risk probability

## Key Tasks
- [ ] Implement Penalized Logistic Regression model
- [ ] Implement Random Forest model
- [ ] Perform cross-validation (stratified k-fold)
- [ ] Tune hyperparameters
- [ ] Calculate performance metrics (accuracy, precision, recall, F1)
- [ ] Save trained models to models/ folder
- [ ] Document model performance and configurations

## Acceptance Criteria
- Both models trained successfully
- Cross-validation completed with metrics reported
- Models saved as .pkl files with version numbers
- Performance metrics documented in models/README.md
- Hyperparameters documented
- Code follows best practices

## Depends On
- #2 (Feature engineering pipeline)

## Resources
- scikit-learn Logistic Regression: https://scikit-learn.org/
- scikit-learn Random Forest: https://scikit-learn.org/
- ml/README.md""",
        "assignees": [""],
        "labels": ["@Nirali-ML", "feature", "ml-model"]
    },
    {
        "title": "Generate SHAP values for model explainability",
        "body": """## Objective
Implement SHAP (SHapley Additive exPlanations) value generation to provide explainability for model predictions.

## SHAP Features to Implement
- [ ] Force plots (individual prediction explanations)
- [ ] Summary plots (global model interpretation)
- [ ] Dependence plots (feature relationships)
- [ ] Feature importance rankings

## Key Tasks
- [ ] Install and configure SHAP library
- [ ] Create SHAP explainer for trained models
- [ ] Generate SHAP values for test dataset
- [ ] Implement SHAP visualization generation
- [ ] Create feature importance plots
- [ ] Document SHAP integration approach
- [ ] Test SHAP output with sample predictions

## Acceptance Criteria
- SHAP values generated successfully for predictions
- Visualizations created and tested
- Integration with backend API ready
- Documentation complete with examples
- Performance tested (generation time acceptable)

## Depends On
- #3 (Model training)

## Resources
- SHAP Documentation: https://shap.readthedocs.io/
- ml/README.md
- frontend/README.md (for visualization requirements)""",
        "assignees": [""],
        "labels": ["@Nirali-ML", "feature", "explainability"]
    },
    {
        "title": "Set up FastAPI backend server and API structure",
        "body": """## Objective
Establish FastAPI backend server with proper routing, validation, and error handling.

## API Structure
- Base URL: `http://localhost:5000`
- Health check: `GET /health`
- Documentation: `GET /docs` (Swagger UI)
- Alternative docs: `GET /redoc` (ReDoc)

## Key Tasks
- [ ] Initialize FastAPI application
- [ ] Set up Uvicorn ASGI server
- [ ] Implement request/response data models using Pydantic
- [ ] Create API documentation (Swagger UI)
- [ ] Implement error handling middleware
- [ ] Set up logging and monitoring
- [ ] Create health check endpoint
- [ ] Configure CORS for frontend access

## Acceptance Criteria
- FastAPI server starts and runs without errors
- Swagger documentation accessible at /docs
- All endpoints return proper HTTP status codes
- Request validation working correctly
- Error messages informative and consistent
- Code follows FastAPI best practices

## Notes
This is foundational work for the backend. Other backend tasks depend on this.

## Resources
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic Validation: https://docs.pydantic.dev/
- backend/README.md""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "feature", "backend-setup"]
    },
    {
        "title": "Create /predict endpoint for mortality risk scoring",
        "body": """## Objective
Implement the main prediction endpoint that takes patient lab values and returns mortality risk score with SHAP explanations.

## Endpoint Specification
**POST /predict**

### Request Body
```json
{
  "bilirubin": 1.5,
  "albumin": 3.8,
  "age": 65,
  "prothrombin_time": 12.5,
  "platelets": 150000
}
```

### Response
```json
{
  "risk_score": 0.35,
  "confidence_interval": [0.28, 0.42],
  "risk_level": "high",
  "shap_values": {...},
  "shap_base_value": 0.25,
  "feature_contributions": {...}
}
```

## Key Tasks
- [ ] Load trained model from models/ folder
- [ ] Validate input data (ranges, types)
- [ ] Preprocess input using feature pipeline
- [ ] Generate prediction with probability
- [ ] Calculate confidence intervals (bootstrap)
- [ ] Generate SHAP values for explanation
- [ ] Format response with all required data
- [ ] Implement error handling for invalid inputs
- [ ] Add logging for all predictions
- [ ] Test with various input scenarios

## Acceptance Criteria
- Endpoint returns accurate predictions
- Response time < 500ms
- Input validation catches invalid data
- Error messages are clear
- SHAP values generated correctly
- Confidence intervals calculated properly
- Integration with frontend tested

## Depends On
- #5 (FastAPI setup)
- #3 (Model training) - ML side
- #4 (SHAP integration) - ML side

## Resources
- FastAPI Documentation: https://fastapi.tiangolo.com/
- backend/README.md""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "feature", "api-endpoint"]
    },
    {
        "title": "Implement model loading and serving with Joblib",
        "body": """## Objective
Set up efficient model loading, caching, and serving from the backend for fast predictions.

## Model Loading Strategy
- Load all models at startup for performance
- Cache models in memory
- Support model versioning
- Graceful error handling for missing models

## Key Tasks
- [ ] Implement model loader using Joblib
- [ ] Load models on server startup (not per request)
- [ ] Create model versioning system
- [ ] Implement model cache/singleton pattern
- [ ] Handle model not found errors gracefully
- [ ] Document model paths and versions
- [ ] Create model health check function
- [ ] Test model loading and inference speed
- [ ] Implement model hot-reload capability (optional)

## Acceptance Criteria
- Models load on server startup
- First prediction < 200ms (after warmup)
- Model version clearly identified
- Error handling for missing/corrupt models
- Model loading tested with all versions
- Documentation clear and complete

## Depends On
- #3 (Model training) - ML side
- #5 (FastAPI setup)

## Resources
- Joblib Documentation: https://joblib.readthedocs.io/
- models/README.md
- backend/README.md""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "feature", "model-serving"]
    },
    {
        "title": "Build Streamlit UI layout and patient input form",
        "body": """## Objective
Create an intuitive and professional Streamlit interface for patient data input and risk score display.

## UI Components to Build
- [ ] Page configuration and title
- [ ] Patient input form with 5 lab value fields
  - Bilirubin (mg/dL): 0.0 - 10.0
  - Albumin (g/dL): 1.0 - 5.0
  - Age (years): 18 - 120
  - Prothrombin Time: 10.0 - 40.0
  - Platelets (10^9/L): 10000 - 500000
- [ ] Input validation and error messages
- [ ] Submit button with loading state
- [ ] Results display section
- [ ] Responsive layout (columns for organization)
- [ ] Professional styling and colors
- [ ] Info/help text for users

## Key Features
- [ ] Form with proper input ranges and validation
- [ ] Loading spinner during prediction
- [ ] Clear display of results
- [ ] User-friendly error messages
- [ ] Mobile-responsive design
- [ ] Accessibility features

## Acceptance Criteria
- All 5 input fields working correctly
- Input validation catches out-of-range values
- Form submits data properly
- Layout is clean and professional
- Error messages are helpful
- Page responsive on different screen sizes
- Code well-documented

## Resources
- Streamlit Documentation: https://docs.streamlit.io/
- frontend/README.md
- onboarding/DEEKSHITHA_FRONTEND_DEVELOPER.md""",
        "assignees": [""],
        "labels": ["@Deekshitha-Frontend", "feature", "ui-frontend"]
    },
    {
        "title": "Integrate frontend with backend API /predict endpoint",
        "body": """## Objective
Connect the Streamlit frontend to the backend /predict endpoint for live predictions.

## Integration Points
- API Base URL: `http://localhost:5000`
- Endpoint: `POST /predict`
- Request timeout: 10 seconds
- Retry attempts: 3

## Key Tasks
- [ ] Import requests library
- [ ] Create API communication functions
- [ ] Handle form submission to backend
- [ ] Parse API response
- [ ] Display risk score with appropriate styling
- [ ] Show confidence intervals
- [ ] Handle API errors gracefully
- [ ] Add retry logic for failed requests
- [ ] Create loading states during API calls
- [ ] Test with backend running

## Error Handling
- [ ] Connection refused errors
- [ ] Invalid response format
- [ ] Server timeout
- [ ] Invalid input data
- [ ] User-friendly error messages

## Acceptance Criteria
- Frontend successfully calls backend API
- Predictions displayed correctly
- Error handling works for all scenarios
- Loading states show proper feedback
- Response time acceptable (< 1 second)
- Integration tested end-to-end

## Depends On
- #8 (UI layout)
- #6 (/predict endpoint) - Backend side

## Resources
- Requests Library: https://requests.readthedocs.io/
- Streamlit Documentation: https://docs.streamlit.io/
- frontend/README.md""",
        "assignees": [""],
        "labels": ["@Deekshitha-Frontend", "feature", "integration"]
    },
    {
        "title": "Display risk scores and SHAP explainability charts",
        "body": """## Objective
Create beautiful and informative visualizations to display mortality risk scores and SHAP explanations.

## Results Display Components
- [ ] Large risk score display with color coding
  - Green: Low risk (< 30%)
  - Yellow: Medium risk (30-60%)
  - Red: High risk (> 60%)
- [ ] Confidence interval display
- [ ] Risk level badge/label
- [ ] SHAP force plot (individual explanation)
- [ ] Feature importance chart (bar plot)
- [ ] Summary statistics

## SHAP Visualizations
- [ ] Force plot showing feature contributions
- [ ] Feature impact on prediction
- [ ] Color-coded contributions (positive/negative)
- [ ] Interactive tooltips with explanations

## Key Features
- [ ] Color-coded risk levels
- [ ] Clear numerical displays
- [ ] Professional charts using Plotly
- [ ] Responsive chart sizing
- [ ] Print-friendly layout
- [ ] Export results capability (optional)

## Acceptance Criteria
- Risk score displayed prominently
- Color coding matches risk levels
- SHAP charts render correctly
- Charts are interactive and clear
- Layout is professional and organized
- Mobile-responsive design
- All text readable and accessible

## Depends On
- #9 (API integration)
- #4 (SHAP integration) - ML side

## Resources
- Streamlit Metrics: https://docs.streamlit.io/
- Plotly Charting: https://plotly.com/python/
- frontend/README.md""",
        "assignees": [""],
        "labels": ["@Deekshitha-Frontend", "feature", "visualization"]
    },
    {
        "title": "Implement model validation and performance testing",
        "body": """## Objective
Create comprehensive validation tests to ensure model accuracy, reliability, and clinical appropriateness.

## Test Categories
### Model Accuracy Tests
- [ ] Accuracy on test dataset
- [ ] Performance on stratified folds
- [ ] Metrics on different patient subgroups
- [ ] Edge case handling (very high/low values)

### Data Validation Tests
- [ ] Input data type validation
- [ ] Value range validation
- [ ] Missing data handling
- [ ] Outlier detection

### System Tests
- [ ] End-to-end prediction pipeline
- [ ] API response validation
- [ ] SHAP value generation

## Validation Tasks
- [ ] Implement accuracy metrics calculation (accuracy, precision, recall, F1)
- [ ] Calculate Brier score for probability predictions
- [ ] Implement confusion matrix analysis
- [ ] Test model on edge cases
- [ ] Verify output ranges (0-1 for probability)
- [ ] Test with missing/invalid data handling
- [ ] Benchmark against baseline model
- [ ] Performance metric logging
- [ ] Create validation report template

## Acceptance Criteria
- All validation tests pass
- Metrics calculated and logged correctly
- Edge cases handled properly
- Report generated with findings
- Performance meets requirements
- Documentation complete

## Resources
- Scikit-learn Metrics: https://scikit-learn.org/
- validation/README.md
- onboarding/RUDRA_VALIDATION_ENGINEER.md""",
        "assignees": [""],
        "labels": ["@Rudra-Validation", "feature", "testing"]
    },
    {
        "title": "Calculate bootstrap confidence intervals for predictions",
        "body": """## Objective
Implement bootstrap resampling to generate confidence intervals for model predictions, providing uncertainty quantification.

## Confidence Interval Calculation
- [ ] 2.5th percentile (lower bound)
- [ ] 97.5th percentile (upper bound)
- [ ] Standard error calculation
- [ ] Bias correction (optional)

## Bootstrap Tasks
- [ ] Implement bootstrap resampling function
- [ ] Resample training data N times (N=1000)
- [ ] Train models on each bootstrap sample
- [ ] Generate predictions from each model
- [ ] Calculate confidence intervals (95%)
- [ ] Integrate with /predict endpoint
- [ ] Test confidence interval coverage
- [ ] Document bootstrap methodology
- [ ] Visualize uncertainty distributions

## Integration Points
- Add CI to /predict response
- Display CI in frontend results
- Include CI in SHAP explanations
- Log CI for all predictions

## Acceptance Criteria
- Bootstrap implemented correctly
- Confidence intervals calculated accurately
- Coverage probability verified (should be ~95%)
- Integration with prediction endpoint working
- Response time acceptable
- Documentation complete with examples

## Resources
- SciPy Bootstrap: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
- Statsmodels Bootstrap: https://www.statsmodels.org/
- validation/README.md""",
        "assignees": [""],
        "labels": ["@Rudra-Validation", "feature", "uncertainty-quantification"]
    },
    {
        "title": "Benchmark model against MELD score (clinical baseline)",
        "body": """## Objective
Compare HepatiQ model performance against the clinical MELD (Model for End-Stage Liver Disease) score baseline.

## MELD Score Background
MELD is a standard clinical scoring system used for liver disease prognosis:
- Formula uses INR, bilirubin, and creatinine
- Score range: 6-40+
- Higher scores = worse prognosis
- Clinical standard for prioritization

## Comparison Metrics
- [ ] ROC-AUC comparison
- [ ] Calibration analysis
- [ ] Decision curve analysis
- [ ] Net benefit calculation
- [ ] Sensitivity/specificity at key thresholds

## Benchmarking Tasks
- [ ] Implement MELD score calculator
- [ ] Calculate MELD scores for test dataset
- [ ] Compare predictions with MELD scores
- [ ] Calculate correlation coefficient
- [ ] Compute performance metrics comparison
- [ ] Statistical significance testing
- [ ] Generate comparison visualizations
- [ ] Document advantages/limitations of each approach
- [ ] Create clinical comparison report

## Deliverables
- [ ] MELD calculator function
- [ ] Comparison report with statistics
- [ ] Visualization comparing both approaches
- [ ] Clinical interpretation document
- [ ] Recommendation on when to use each method

## Acceptance Criteria
- MELD calculator implemented correctly
- Comparison metrics calculated accurately
- Statistical tests performed appropriately
- Report is comprehensive and clinical
- Visualizations are clear and professional
- Documentation explains findings clearly

## Resources
- MELD Score Info: https://en.wikipedia.org/wiki/Model_for_End-Stage_Liver_Disease
- SciPy Stats: https://docs.scipy.org/doc/scipy/reference/stats.html
- validation/README.md""",
        "assignees": [""],
        "labels": ["@Rudra-Validation", "feature", "clinical-validation"]
    }
]

def create_issue(title: str, body: str, labels: list, assignees: Optional[list] = None) -> dict:
    """Create a single issue in the repository"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "title": title,
        "body": body,
        "labels": labels
    }
    
    if assignees and assignees[0]:
        payload["assignees"] = assignees
    
    url = f"{API_URL}/repos/{REPO}/issues"
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 201:
        return {"success": True, "issue": response.json()}
    else:
        return {"success": False, "error": response.json()}

def main():
    print(f"Creating {len(issues_data)} issues in {REPO}...\n")
    
    for i, issue in enumerate(issues_data, 1):
        result = create_issue(
            title=issue["title"],
            body=issue["body"],
            labels=issue["labels"],
            assignees=issue["assignees"]
        )
        
        if result["success"]:
            issue_num = result["issue"]["number"]
            print(f"✅ #{issue_num}: {issue['title']}")
        else:
            print(f"❌ Failed: {issue['title']}")
            print(f"   Error: {result['error']}")
    
    print(f"\nDone! Visit: https://github.com/{REPO}/issues")

if __name__ == "__main__":
    main()

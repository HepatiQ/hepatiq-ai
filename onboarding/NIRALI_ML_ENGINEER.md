# 🚀 COMPLETE ONBOARDING GUIDE FOR NIRALI - ML Engineer

# Welcome Nirali! 👋

This is your complete start-from-scratch guide to get you up and running.

## YOUR ROLE: Data & ML Lead
- Focus: Data cleaning, model training, SHAP integration, feature engineering

---

## STEP 1: INSTALL REQUIRED TOOLS (15 minutes)

Download and install these:

1️⃣ **Git** (Version Control)
   - Download: https://git-scm.com/
   
2️⃣ **Python 3.8 or higher**
   - Download: https://www.python.org/
   - ⚠️ CHECK: "Add Python to PATH" during installation
   
3️⃣ **VS Code** (Code Editor)
   - Download: https://code.visualstudio.com/
   
4️⃣ **GitHub Account**
   - Sign up: https://github.com/signup

**Verify Installation:**
```bash
git --version
python --version
```

---

## STEP 2: CONFIGURE GIT (2 minutes)

Open terminal and run:
```bash
git config --global user.name "Nirali"
git config --global user.email "your.email@example.com"
```

Replace with your actual name and email!

---

## STEP 3: CLONE THE PROJECT (5 minutes)

```bash
mkdir projects
cd projects
git clone https://github.com/HepatiQ/hepatiq-ai.git
cd hepatiq-ai
```

Verify it worked:
```bash
ls    # Mac/Linux
dir   # Windows
```

---

## STEP 4: SET UP PYTHON ENVIRONMENT (10 minutes)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

✓ Success: You'll see `(venv)` at the start of your terminal line

---

## STEP 5: INSTALL ALL PACKAGES (5 minutes)

```bash
pip install -r requirements.txt
```

Wait for it to finish!

---

## STEP 6: OPEN PROJECT IN VS CODE

```bash
code .
```

---

## STEP 7: UNDERSTAND YOUR ROLE

**YOU ARE:** Data & ML Lead

**WHAT YOU DO:**
- ✓ Data cleaning and preprocessing
- ✓ Feature engineering
- ✓ Train ML models (Logistic Regression, Random Forest)
- ✓ Generate SHAP values for explainability
- ✓ Document model architecture and metrics
- ✓ Save trained models to models/ folder

**TOOLS YOU'LL USE:**
- Pandas & NumPy - Data loading and cleaning
- Scikit-learn - Model training, imputation, scaling
- SHAP - Model explainability
- Joblib - Model serialization

**YOUR KEY TASKS:**
1. Load and clean Mayo Clinic PBC dataset
2. Implement feature engineering
3. Train models with cross-validation
4. Generate SHAP explanations
5. Document performance metrics

---

## STEP 8: READ THE DOCUMENTATION

Open these files in order:

1. **README.md** (3 min)
   - Understand what HepatiQ does
   - See the tech stack
   - Learn system flow

2. **ml/README.md** (5 min)
   - Understand your responsibilities
   - See development guidelines
   - Learn model management

3. **data/README.md** (3 min)
   - Understand dataset organization
   - See data privacy requirements

4. **docs/TEAM_WORKFLOW.md** (5 min)
   - Learn branching strategy
   - See pull request workflow

---

## STEP 9: RUN YOUR FIRST TRAINING

```bash
# Make sure virtual environment is activated (venv)
python ml/train.py
```

Expected Output:
```
Training model...
Model accuracy: XX%
Model saved to models/
```

---

## STEP 10: MAKE YOUR FIRST CHANGE

1. Create a new branch:
```bash
git checkout -b nirali-ml-training
```

2. Open `ml/train.py` and add a comment at the top:
```python
# ML Training Pipeline by Nirali - [Date]
```

3. Save the file

4. Add your changes:
```bash
git add .
git commit -m "Start ML training pipeline - Nirali"
git push origin nirali-ml-training
```

---

## STEP 11: CREATE A PULL REQUEST

1. Go to: https://github.com/HepatiQ/hepatiq-ai/pulls
2. Click "New Pull Request"
3. Select your branch: `nirali-ml-training`
4. Add title: "Initialize ML training pipeline"
5. Click "Create Pull Request"

---

## STEP 12: DAILY COMMANDS

**Start of day:**
```bash
cd hepatiq-ai
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate        # Windows
git pull origin main
code .
```

**Work:**
```bash
git checkout -b your-branch
# Make changes...
python ml/train.py          # Test your code
```

**End of day:**
```bash
git add .
git commit -m "What you did"
git push origin your-branch
deactivate
```

---

## STEP 13: TROUBLESHOOTING

❌ **"Python not found"**
- Restart terminal
- Try: `python3 --version`

❌ **"Packages won't install"**
- Is venv activated? (check for `(venv)`)
- Run: `pip install --upgrade pip`
- Then: `pip install -r requirements.txt`

❌ **"Import errors"**
- Virtual environment activated?
- Run: `pip install -r requirements.txt`

---

## NEXT STEPS

✅ **NOW DO:**

1. Read these files:
   - [ ] ml/README.md
   - [ ] data/README.md
   - [ ] docs/TEAM_WORKFLOW.md

2. Explore the codebase:
   - [ ] Open ml/train.py
   - [ ] Open data/ folder
   - [ ] Check data structure

3. Run your first training:
   - [ ] Run: `python ml/train.py`
   - [ ] Check output

4. Create your first issue on GitHub

5. Ask questions in comments!

---

## RESOURCES

📖 **Learn Python:**
https://docs.python.org/3/tutorial/

📖 **Scikit-learn Docs:**
https://scikit-learn.org/

📖 **SHAP Documentation:**
https://shap.readthedocs.io/

📖 **Git Guide:**
https://git-scm.com/book/en/v2

---

## 🎉 YOU'RE ALL SET!

Questions? Comment below! 👇

Good luck Nirali! Let's build something amazing! 🚀
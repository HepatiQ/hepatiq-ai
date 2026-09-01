# 🎨 COMPLETE ONBOARDING GUIDE FOR DEEKSHITHA - Frontend UI Developer

# Welcome Deekshitha! 👋

This is your complete start-from-scratch guide to get you up and running.

## YOUR ROLE: Frontend UI Developer
- Focus: Streamlit interface, user experience, beautiful dashboards, patient forms

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
   - Install extension: "Python" by Microsoft
   
4️⃣ **GitHub Account**
   - Sign up: https://github.com/signup

**Verify Installation:**
```bash
git --version
python --version
```

---

## STEP 2: CONFIGURE GIT

```bash
git config --global user.name "Deekshitha"
git config --global user.email "your.email@example.com"
```

---

## STEP 3: CLONE THE PROJECT

```bash
mkdir projects
cd projects
git clone https://github.com/HepatiQ/hepatiq-ai.git
cd hepatiq-ai
```

---

## STEP 4: SET UP PYTHON ENVIRONMENT

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

---

## STEP 5: INSTALL ALL PACKAGES

```bash
pip install -r requirements.txt
```

---

## STEP 6: UNDERSTAND YOUR ROLE

**YOU ARE:** Frontend UI Developer

**WHAT YOU DO:**
- ✓ Build beautiful, user-friendly interfaces
- ✓ Create patient input forms
- ✓ Display results and risk scores
- ✓ Show SHAP explainability charts
- ✓ Make it responsive and accessible
- ✓ Connect to backend API

**TOOLS YOU'LL USE:**
- **Streamlit** - Fast web app framework (Python-based!)
- **Requests** - Communicate with backend API
- **Plotly/Matplotlib** - Visualizations
- **Pandas** - Display data nicely

**YOUR KEY TASKS:**
1. Create patient lab value input form (5 fields)
2. Add "Submit" button to send data to backend
3. Display risk score result
4. Show SHAP explainability chart
5. Add error handling
6. Make it beautiful and easy to use!

---

## STEP 7: LEARN STREAMLIT (20 minutes)

Streamlit is a Python framework for building web apps easily!

**STREAMLIT BASICS:**

```python
# Text & Headers
st.title("HepatiQ - Risk Calculator")
st.header("Patient Data")
st.write("Enter lab values below")

# Input Fields
bilirubin = st.number_input("Bilirubin (mg/dL)", 0.0, 10.0)
albumin = st.number_input("Albumin (g/dL)", 1.0, 5.0)

# Buttons
if st.button("Calculate Risk"):
    # Do something

# Display Results
st.success("Risk calculated!")
st.metric("Mortality Risk", "35%", "High")

# Charts
import plotly.express as px
fig = px.bar(data)
st.plotly_chart(fig)
```

📖 **Full Streamlit Docs:** https://docs.streamlit.io/

---

## STEP 8: RUN THE FRONTEND APP

```bash
python frontend/app.py
```

OR:
```bash
streamlit run frontend/app.py
```

Open browser: **http://localhost:8501**

---

## STEP 9: UNDERSTAND THE BACKEND API

Your frontend talks to the backend API:

**ENDPOINT:** `POST /predict`

**REQUEST (what frontend sends):**
```json
{
  "bilirubin": 1.5,
  "albumin": 3.8,
  "age": 65,
  "prothrombin_time": 12.5,
  "platelets": 150000
}
```

**RESPONSE (what backend returns):**
```json
{
  "risk_score": 0.35,
  "confidence_interval": [0.28, 0.42],
  "shap_values": {...},
  "shap_explanation": {...}
}
```

**In your Streamlit code:**
```python
import requests

data = {
    "bilirubin": bilirubin,
    "albumin": albumin,
    ...
}

response = requests.post("http://localhost:5000/predict", json=data)
result = response.json()

st.metric("Risk Score", f"{result['risk_score']*100:.1f}%")
```

---

## STEP 10: MAKE YOUR FIRST CHANGE

```bash
git checkout -b deekshitha-frontend-ui

# Edit frontend/app.py
# Add at top:
# st.set_page_config(page_title="HepatiQ", layout="wide")
# st.title("🏥 HepatiQ - Mortality Risk Calculator")

# Test it
python frontend/app.py
# Go to http://localhost:8501

git add .
git commit -m "Add UI improvements - Deekshitha"
git push origin deekshitha-frontend-ui
```

---

## STEP 11: CREATE A PULL REQUEST

1. Go to: https://github.com/HepatiQ/hepatiq-ai/pulls
2. Click "New Pull Request"
3. Select your branch: `deekshitha-frontend-ui`
4. Click "Create Pull Request"

---

## STEP 12: STREAMLIT COMPONENTS YOU'LL USE

**INPUT COMPONENTS:**
```python
st.number_input()       # For lab values
st.slider()             # For ranges
st.text_input()         # For text
st.selectbox()          # For dropdown
st.button()             # For actions
```

**DISPLAY COMPONENTS:**
```python
st.write()              # Display text
st.title()              # Big heading
st.metric()             # Display metrics
st.success()            # Green message
st.error()              # Red error
st.warning()            # Yellow warning
```

**CHARTS:**
```python
st.plotly_chart()       # Interactive charts
st.bar_chart()          # Bar chart
st.line_chart()         # Line chart
```

**LAYOUT:**
```python
st.columns()            # Side-by-side
st.tabs()               # Tabbed interface
st.sidebar              # Left sidebar
```

---

## STEP 13: DAILY COMMANDS

**Start of day:**
```bash
cd hepatiq-ai
source venv/bin/activate
git pull origin main
code .
```

**Work:**
```bash
git checkout -b your-branch
# Edit frontend/app.py
python frontend/app.py
# Open http://localhost:8501
```

**End of day:**
```bash
git add .
git commit -m "What you built"
git push origin your-branch
deactivate
```

---

## NEXT STEPS

1. Learn Streamlit basics: https://docs.streamlit.io/
2. Run current app: `python frontend/app.py`
3. Read: frontend/README.md
4. Design your UI layout on paper
5. Create issue: "Build patient input form"
6. Ask questions!

---

## TROUBLESHOOTING

❌ **"Port 8501 already in use"**
- Close other Streamlit windows
- Run: `streamlit run frontend/app.py --server.port 8502`

❌ **"Backend not running"**
- Make sure backend is running in another terminal
- Run: `python backend/main.py`

❌ **"Import error"**
- Virtual environment activated?
- Run: `pip install -r requirements.txt`

---

## RESOURCES

📖 **Streamlit Docs:**
https://docs.streamlit.io/

📖 **Streamlit Gallery:**
https://streamlit.io/gallery

📖 **Plotly Charts:**
https://plotly.com/python/

📖 **Git Guide:**
https://git-scm.com/book/en/v2

---

## 🎉 YOU'RE ALL SET!

Questions? Comment below! 👇

Good luck Deekshitha! Let's build something beautiful! 🚀
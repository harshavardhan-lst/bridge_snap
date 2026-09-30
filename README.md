# BridgeSnap 🏗️
### VLM-Based Preliminary Bridge Damage Assessment and Visual Condition Analysis

BridgeSnap is an AI vision application built with **Streamlit** and **Google Gemini Vision-Language Models (VLMs)**. It assists civil engineers, students, and infrastructure inspectors by providing preliminary, image-based visual damage detection, classification, apparent severity estimation, and conversational inspection analysis.

---

## 🌟 Key Capabilities
- **Multimodal Visual Inspection**: Upload field photos of bridge decks, piers, abutments, girders, or bearing seats.
- **Structured Damage Assessment**:
  1. **Damage Present**: Yes / No / Uncertain
  2. **Apparent Damage Type**: Crack / Spalling / Corrosion / Exposed Reinforcement / Surface Deterioration / Delamination
  3. **Approximate Location**: Specific visible component region
  4. **Apparent Visual Severity**: Low / Moderate / High / Uncertain
  5. **Visual Evidence & Reasoning**: Observable color changes, spall edges, rust staining, and fissure patterns
  6. **Confidence & Limitations**: Optical factors (lighting, angle, resolution, lack of scale)
  7. **Engineering Scope**: Calibrated disclaimers stating that visual analysis does not constitute full structural certification.
- **Conversational Multi-Turn Memory**: Ask follow-up technical questions about previously analyzed components.
- **Preliminary Condition Reports**: Generate and download structured markdown assessment reports.
- **Resilient Multi-Model Architecture**: Seamless automatic failover across low-traffic Gemini vision models (`gemini-3-flash-preview`, `gemini-3.1-flash-lite`, etc.).

---

## 📁 Repository Structure
```
bridge_snap/
├── app.py                      # Main Streamlit web application & chat pipeline
├── prompts.py                  # Domain system instructions, schemas & report templates
├── requirements.txt            # Minimal Python dependencies
├── .gitignore                  # Keeps secrets.toml and virtual environments private
└── .streamlit/
    ├── secrets.toml.example    # Configuration template
    └── secrets.toml            # Private API keys (git-ignored)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/harshavardhan-lst/bridge_snap.git
cd bridge_snap

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # On Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

### 3. API Key Setup
Copy the template to `.streamlit/secrets.toml`:
```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```
Fill in your API key in `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
MODEL_NAME = "gemini-3-flash-preview"
```

### 4. Run Locally
```powershell
python -m streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## ⚠️ Academic & Structural Safety Disclaimer
BridgeSnap is a preliminary computational visual decision-support tool. 2D photographic visual inference cannot assess internal concrete integrity, subsurface voids, or structural load capacity. Certified on-site non-destructive testing (NDT) by licensed structural engineers is required for all formal safety assessments.

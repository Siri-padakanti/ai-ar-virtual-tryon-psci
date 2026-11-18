# AI-Powered AR Virtual Try-On with PSCI

This repository houses the  B.Tech project: **AI-Powered AR Virtual Try-On with Personalized Style Compatibility Index (PSCI)**.

---

## Current Status: Module 1 (Step 1 Completed)
We are implementing the project **one module and one step at a time**.
We have completed **Step 1: Project Scaffolding and Environment Setup**. 
Only project folder structures, configurations, startup scripts, and placeholder files have been created. No model, webcam, or computational logic has been written yet.

---

## Folder Structure

* `data/`: Local storage for dataset mini-subsets (created during Step 2).
* `models/`: Neural network architecture files and weight checkpoint folders.
* `src/backend/`: FastAPI server files.
  * `app.py`: FastAPI endpoints skeleton.
  * `ar_engine.py`: Pose tracking and TPS warping placeholder.
  * `segmentation.py`: Background removal placeholder.
  * `vton_pipeline.py`: Deep try-on execution placeholder.
  * `utils.py`: Image and dataset unzipping helpers.
* `src/frontend/`: React + Vite client dashboard.
* `run.py`: Multi-server startup script.

---

## Getting Started

### 1. Backend Setup
Create a virtual environment and install Python requirements:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Frontend Setup
Install npm packages:
```powershell
cd src/frontend
npm install
cd ../..
```

### 3. Running the Project
Launch both servers simultaneously:
```powershell
python run.py
```
Open `http://localhost:5173` in your browser.

# AI Data Quality Analyzer

A full-stack web application that lets users upload datasets (CSV/Excel), profiles data quality, provides AI-powered recommendations, and offers automated cleaning with export capabilities.

## Features

- 📊 **Comprehensive Profiling**: Detects missing values, duplicates, outliers, mixed data types, and invalid values.
- 🎯 **Quality Scoring**: Calculates a weighted score (0-100) based on completeness, uniqueness, validity, consistency, and accuracy.
- 🤖 **AI Recommendations**: Context-aware, rule-based engine that maps detected issues to actionable fixes.
- 🧹 **Automated Cleaning**: Apply targeted fixes (imputation, deduplication, outlier handling, type conversion, standardization) with before/after comparisons.
- 📥 **Export**: Download the cleaned dataset (CSV/Excel) and a professional PDF quality report.
- 🎨 **Modern UI**: Premium dark-theme glassmorphism dashboard built with vanilla web technologies.

## Tech Stack

- **Backend**: Python 3.x, Flask, Pandas, NumPy, SciPy, ReportLab
- **Frontend**: HTML5, Vanilla CSS, Vanilla JS, Chart.js

## Project Structure

```
AI DATA QUALITY ANALYZER/
├── backend/
│   ├── app.py              # Flask application and API endpoints
│   ├── analyzer.py         # Data quality analysis engine
│   ├── cleaner.py          # Dataset cleaning engine
│   ├── recommender.py      # AI recommendation engine
│   ├── report_generator.py # PDF report generator
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Single-page application shell
│   ├── styles.css          # Premium dark-theme design system
│   └── app.js              # Application logic and UI state
├── run.bat                 # Windows one-click launcher
└── README.md
```

## Setup & Running

### Option 1: One-Click (Windows)
Double-click the `run.bat` file in the root directory. It will automatically install dependencies and start the server.

### Option 2: Manual Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start the Flask server:**
   ```bash
   python app.py
   ```

3. **Open the Application:**
   Open your browser and navigate to: `http://localhost:5000`

## Usage Workflow

1. Open the application in your browser.
2. Drag and drop a CSV or Excel file to upload.
3. Review the **Overview** dashboard and **Column Analysis**.
4. Check the **Issues** tab to see detected problems prioritized by severity.
5. Review the **AI Insights** for contextual explanations and suggested fixes.
6. Go to the **Clean** tab, select the operations you want to apply, and click "Apply Selected Operations".
7. Review the before/after results and the cleaned data preview.
8. Go to the **Export** tab to download your cleaned dataset and PDF report.

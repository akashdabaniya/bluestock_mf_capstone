# 📊 Bluestock Mutual Fund Capstone Project

A comprehensive data engineering and analytics capstone project focused on Indian mutual fund data — covering ETL pipelines, live NAV tracking, data quality reporting, and analytical dashboards.

---

## 📁 Project Structure

```
bluestock_mf_capstone/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/                 # Raw data fetched from MFAPI / AMFI
│   ├── processed/           # Cleaned and merged datasets
│   └── db/                  # SQLite databases
├── notebooks/               # Jupyter notebooks for EDA and analysis
├── scripts/
│   ├── etl_pipeline.py      # Main ETL pipeline (Day 1 — D1)
│   └── live_nav_fetch.py    # Live NAV fetcher utility
├── sql/                     # SQL scripts for schema & queries
├── dashboard/               # Dashboard assets (Plotly / Streamlit)
└── reports/                 # Generated reports and summaries
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd bluestock_mf_capstone
pip install -r requirements.txt
```

### 2. Run the Day 1 ETL Pipeline

```bash
python scripts/etl_pipeline.py
```

This will:
- Create the full folder structure if not present
- Download the complete AMFI fund master list → `data/raw/fund_master.csv`
- Fetch NAV history for 10 key schemes → `data/raw/nav_{code}.csv`
- Merge into a combined NAV history → `data/processed/combined_nav_history.csv`
- Validate AMFI codes and log data quality issues
- Write a data-quality summary → `reports/data_quality_summary.txt`

### 3. Fetch Live NAV Data

```bash
python scripts/live_nav_fetch.py
```

Fetches the latest (most-recent) NAV for 6 key schemes and saves:
- Individual files → `data/raw/live_nav_{code}.csv`
- Consolidated summary → `data/processed/live_nav_summary.csv`

---

## 📡 Data Sources

| Source | URL | Description |
|--------|-----|-------------|
| MFAPI | `https://api.mfapi.in/mf/{scheme_code}` | Historical & current NAV for any AMFI scheme |
| AMFI Master List | `https://api.mfapi.in/mf` | Full catalogue of all registered mutual fund schemes |

---

## 🏦 Key Schemes Tracked

| Scheme Name | AMFI Code |
|-------------|-----------|
| HDFC Top 100 Direct | 125497 |
| SBI Bluechip Direct | 119551 |
| ICICI Bluechip Direct | 120503 |
| Nippon Large Cap Direct | 118632 |
| Axis Bluechip Direct | 119092 |
| Kotak Bluechip Direct | 120841 |
| HDFC Mid-Cap Opportunities Direct | 118989 |
| Parag Parikh Flexi Cap Direct | 122639 |
| Mirae Asset Large Cap Direct | 118834 |
| SBI Small Cap Direct | 125497 |

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Data:** pandas · NumPy · SciPy
- **Visualisation:** Matplotlib · Seaborn · Plotly
- **Storage:** SQLite via SQLAlchemy · CSV / Excel (openpyxl)
- **API:** requests (with retry & rate-limit logic)
- **Notebooks:** Jupyter

---

## 📋 Day-wise Deliverables

| Day | Deliverable | Weight | Status |
|-----|-------------|--------|--------|
| 1 | ETL Pipeline + Data Ingestion | 15 % | ✅ Complete |
| 2 | Data Cleaning & SQL Database Design | 20 % | ✅ Complete |
| 3 | Exploratory Data Analysis (EDA) | 20 % | ✅ Complete |
| 4 | Fund Performance Analytics | 20 % | ✅ Complete |
| 5 | Final Report & Presentation | 25 % | 🔲 Pending |

---

## 👤 Author

**Akash Dabaniya**
[GitHub: @akashdabaniya](https://github.com/akashdabaniya)
_Bluestock Fintech — Mutual Fund Analytics Capstone_

---

## 📄 License

This project is part of an academic capstone programme. All data is sourced from publicly available AMFI / MFAPI endpoints.

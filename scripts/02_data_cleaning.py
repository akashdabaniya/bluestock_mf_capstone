import pandas as pd
from pathlib import Path
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIR_RAW = PROJECT_ROOT / "data" / "raw"
DIR_PROCESSED = PROJECT_ROOT / "data" / "processed"

def clean_nav_history():
    logger.info("Cleaning nav_history.csv...")
    df = pd.read_csv(DIR_RAW / "02_nav_history.csv")
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['amfi_code', 'date']).reset_index(drop=True)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['amfi_code', 'date'])
    
    # Validate NAV > 0
    df = df[df['nav'] > 0]
    
    # Forward-fill missing NAV for holidays/weekends
    # To do this correctly, we need to reindex for each amfi_code
    cleaned_frames = []
    for code, group in df.groupby('amfi_code'):
        min_date, max_date = group['date'].min(), group['date'].max()
        full_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        
        group = group.set_index('date').reindex(full_date_range)
        group['amfi_code'] = code
        group['nav'] = group['nav'].ffill()
        
        group = group.reset_index().rename(columns={'index': 'date'})
        cleaned_frames.append(group)
        
    df_clean = pd.concat(cleaned_frames, ignore_index=True)
    df_clean.to_csv(DIR_PROCESSED / "02_nav_history_clean.csv", index=False)
    logger.info(f"nav_history cleaned and saved. Shape: {df_clean.shape}")

def clean_investor_transactions():
    logger.info("Cleaning investor_transactions.csv...")
    df = pd.read_csv(DIR_RAW / "08_investor_transactions.csv")
    
    # standardise transaction_type
    df['transaction_type'] = df['transaction_type'].str.strip().str.title()
    df.loc[df['transaction_type'].str.contains('Sip', case=False, na=False), 'transaction_type'] = 'SIP'
    
    valid_types = ['SIP', 'Lumpsum', 'Redemption']
    df = df[df['transaction_type'].isin(valid_types)]
    
    # validate amount > 0
    df = df[df['amount_inr'] > 0]
    
    # fix date formats
    df['transaction_date'] = pd.to_datetime(df['transaction_date'], format="mixed")
    
    # check KYC status enum values
    df['kyc_status'] = df['kyc_status'].str.upper().str.strip()
    df = df[df['kyc_status'].isin(['VERIFIED', 'PENDING', 'REJECTED'])]
    
    df.to_csv(DIR_PROCESSED / "08_investor_transactions_clean.csv", index=False)
    logger.info(f"investor_transactions cleaned and saved. Shape: {df.shape}")

def clean_scheme_performance():
    logger.info("Cleaning scheme_performance.csv...")
    df = pd.read_csv(DIR_RAW / "07_scheme_performance.csv")
    
    # validate return values are numeric
    return_cols = ['return_1yr_pct', 'return_3yr_pct', 'return_5yr_pct', 'benchmark_3yr_pct']
    for col in return_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # flag anomalies
    df['is_anomaly'] = False
    # If 1yr return > 100% or < -50% for example, just a simple flag
    df.loc[(df['return_1yr_pct'] > 100) | (df['return_1yr_pct'] < -50), 'is_anomaly'] = True
    
    # check expense_ratio range (0.1% – 2.5%)
    df = df[(df['expense_ratio_pct'] >= 0.1) & (df['expense_ratio_pct'] <= 2.5)]
    
    df.to_csv(DIR_PROCESSED / "07_scheme_performance_clean.csv", index=False)
    logger.info(f"scheme_performance cleaned and saved. Shape: {df.shape}")

def copy_other_files():
    import shutil
    files = [
        "01_fund_master.csv", "03_aum_by_fund_house.csv", "04_monthly_sip_inflows.csv",
        "05_category_inflows.csv", "06_industry_folio_count.csv", "09_portfolio_holdings.csv",
        "10_benchmark_indices.csv"
    ]
    for f in files:
        src = DIR_RAW / f
        dst = DIR_PROCESSED / f.replace(".csv", "_clean.csv")
        if src.exists():
            shutil.copy(src, dst)
            logger.info(f"Copied {f} to {dst.name}")

if __name__ == "__main__":
    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    clean_nav_history()
    clean_investor_transactions()
    clean_scheme_performance()
    copy_other_files()
    logger.info("Data Cleaning complete!")

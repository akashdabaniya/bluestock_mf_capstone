import pandas as pd
import sqlite3
from sqlalchemy import create_engine
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
DIR_PROCESSED = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROJECT_ROOT / "bluestock_mf.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

def load_schema(engine):
    logger.info("Loading schema.sql into database...")
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema_sql)
    logger.info("Schema loaded successfully.")

def load_dim_fund(engine):
    df = pd.read_csv(DIR_PROCESSED / "01_fund_master_clean.csv")
    df.to_sql('dim_fund', con=engine, if_exists='append', index=False)
    logger.info(f"Loaded {len(df)} rows into dim_fund.")

def build_and_load_dim_date(engine):
    logger.info("Building dim_date from transaction and nav dates...")
    nav = pd.read_csv(DIR_PROCESSED / "02_nav_history_clean.csv", usecols=['date'])
    txn = pd.read_csv(DIR_PROCESSED / "08_investor_transactions_clean.csv", usecols=['transaction_date'])
    txn = txn.rename(columns={'transaction_date': 'date'})
    
    all_dates = pd.concat([nav, txn])['date'].dropna().unique()
    df_dates = pd.DataFrame({'date': pd.to_datetime(all_dates)})
    df_dates = df_dates.sort_values('date').reset_index(drop=True)
    
    df_dates['year'] = df_dates['date'].dt.year
    df_dates['month'] = df_dates['date'].dt.month
    df_dates['day'] = df_dates['date'].dt.day
    df_dates['quarter'] = df_dates['date'].dt.quarter
    df_dates['day_of_week'] = df_dates['date'].dt.dayofweek
    df_dates['is_weekend'] = df_dates['day_of_week'].isin([5, 6])
    
    df_dates['date'] = df_dates['date'].dt.strftime('%Y-%m-%d')
    df_dates.to_sql('dim_date', con=engine, if_exists='append', index=False)
    logger.info(f"Loaded {len(df_dates)} rows into dim_date.")

def load_fact_nav(engine):
    df = pd.read_csv(DIR_PROCESSED / "02_nav_history_clean.csv")
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df.to_sql('fact_nav', con=engine, if_exists='append', index=False)
    logger.info(f"Loaded {len(df)} rows into fact_nav.")

def load_fact_transactions(engine):
    df = pd.read_csv(DIR_PROCESSED / "08_investor_transactions_clean.csv")
    df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d')
    df.to_sql('fact_transactions', con=engine, if_exists='append', index=False)
    logger.info(f"Loaded {len(df)} rows into fact_transactions.")

def load_fact_performance(engine):
    df = pd.read_csv(DIR_PROCESSED / "07_scheme_performance_clean.csv")
    # select only columns relevant for fact_performance
    cols = ['amfi_code', 'return_1yr_pct', 'return_3yr_pct', 'return_5yr_pct', 
            'benchmark_3yr_pct', 'alpha', 'beta', 'sharpe_ratio', 'sortino_ratio', 
            'std_dev_ann_pct', 'max_drawdown_pct', 'aum_crore', 'morningstar_rating', 
            'risk_grade', 'is_anomaly']
    df_perf = df[cols]
    df_perf.to_sql('fact_performance', con=engine, if_exists='append', index=False)
    logger.info(f"Loaded {len(df_perf)} rows into fact_performance.")

def load_fact_aum(engine):
    df = pd.read_csv(DIR_PROCESSED / "03_aum_by_fund_house_clean.csv")
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df.to_sql('fact_aum', con=engine, if_exists='append', index=False)
    logger.info(f"Loaded {len(df)} rows into fact_aum.")

if __name__ == "__main__":
    if DB_PATH.exists():
        DB_PATH.unlink()
        
    engine = create_engine(f'sqlite:///{DB_PATH}')
    
    load_schema(engine)
    load_dim_fund(engine)
    build_and_load_dim_date(engine)
    load_fact_nav(engine)
    load_fact_transactions(engine)
    load_fact_performance(engine)
    load_fact_aum(engine)
    
    logger.info("Database load complete!")

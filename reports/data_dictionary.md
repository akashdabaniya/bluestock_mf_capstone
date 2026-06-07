# Data Dictionary - Bluestock MF Capstone

## 1. dim_fund
| Column | Data Type | Description |
|---|---|---|
| amfi_code | INTEGER | Primary Key. Unique identifier for the mutual fund scheme as per AMFI. |
| fund_house | TEXT | Name of the Asset Management Company (AMC). |
| scheme_name | TEXT | Full name of the mutual fund scheme. |
| category | TEXT | Broad category of the fund (e.g., Equity, Debt). |
| sub_category | TEXT | Specific sub-category (e.g., Large Cap, Mid Cap). |
| plan | TEXT | Plan type (Direct/Regular). |
| launch_date | DATE | Inception date of the scheme. |
| benchmark | TEXT | Benchmark index for the scheme. |
| expense_ratio_pct | REAL | Annual fee charged by the fund house (%). |
| exit_load_pct | REAL | Fee charged if withdrawn before a specified period (%). |
| min_sip_amount | REAL | Minimum amount for a SIP investment. |
| min_lumpsum_amount | REAL | Minimum amount for a Lumpsum investment. |
| fund_manager | TEXT | Name of the primary fund manager. |
| risk_category | TEXT | Risk classification (e.g., Very High). |
| sebi_category_code | TEXT | SEBI assigned category code. |

## 2. dim_date
| Column | Data Type | Description |
|---|---|---|
| date | DATE | Primary Key. Date in YYYY-MM-DD format. |
| year | INTEGER | Calendar year. |
| month | INTEGER | Calendar month (1-12). |
| day | INTEGER | Day of the month (1-31). |
| quarter | INTEGER | Quarter of the year (1-4). |
| day_of_week | INTEGER | Day of the week (0=Monday, 6=Sunday). |
| is_weekend | BOOLEAN | True if Saturday or Sunday, else False. |

## 3. fact_nav
| Column | Data Type | Description |
|---|---|---|
| amfi_code | INTEGER | Foreign Key to dim_fund. |
| date | DATE | Foreign Key to dim_date. |
| nav | REAL | Net Asset Value of the fund on that date. |

## 4. fact_transactions
| Column | Data Type | Description |
|---|---|---|
| transaction_id | INTEGER | Primary Key. Unique ID for the transaction. |
| investor_id | INTEGER | Unique ID of the investor. |
| transaction_date | DATE | Foreign Key to dim_date. Date of transaction. |
| amfi_code | INTEGER | Foreign Key to dim_fund. Scheme invested in. |
| transaction_type | TEXT | Type of transaction: 'SIP', 'Lumpsum', 'Redemption'. |
| amount_inr | REAL | Transaction amount in INR. |
| state | TEXT | State of the investor. |
| city | TEXT | City of the investor. |
| city_tier | TEXT | City classification (e.g., Tier 1, Tier 2). |
| age_group | TEXT | Age bracket of the investor. |
| gender | TEXT | Gender of the investor. |
| annual_income_lakh | REAL | Annual income of the investor in Lakhs INR. |
| payment_mode | TEXT | Mode of payment (UPI, NetBanking, etc.). |
| kyc_status | TEXT | KYC status of the investor (VERIFIED, PENDING, REJECTED). |

## 5. fact_performance
| Column | Data Type | Description |
|---|---|---|
| amfi_code | INTEGER | Foreign Key to dim_fund. |
| return_1yr_pct | REAL | 1-Year annualized return (%). |
| return_3yr_pct | REAL | 3-Year annualized return (%). |
| return_5yr_pct | REAL | 5-Year annualized return (%). |
| benchmark_3yr_pct | REAL | Benchmark 3-Year return for comparison. |
| alpha | REAL | Fund's excess return over benchmark. |
| beta | REAL | Measure of fund volatility relative to market. |
| sharpe_ratio | REAL | Risk-adjusted return measure. |
| sortino_ratio | REAL | Downside risk-adjusted return. |
| std_dev_ann_pct | REAL | Annualized standard deviation (volatility). |
| max_drawdown_pct | REAL | Maximum peak-to-trough drop in NAV (%). |
| aum_crore | REAL | Assets Under Management in Crores INR. |
| morningstar_rating | INTEGER | Morningstar rating (1 to 5). |
| risk_grade | TEXT | Morningstar risk grade. |
| is_anomaly | BOOLEAN | Flag for anomalous performance metrics. |

## 6. fact_aum
| Column | Data Type | Description |
|---|---|---|
| id | INTEGER | Primary Key. |
| date | DATE | Foreign Key to dim_date. |
| fund_house | TEXT | Name of the fund house. |
| aum_lakh_crore | REAL | AUM in Lakh Crores INR. |
| aum_crore | REAL | AUM in Crores INR. |
| num_schemes | INTEGER | Number of schemes under the fund house. |

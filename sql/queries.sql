-- sql/queries.sql
-- 10 Analytical SQL Queries for Bluestock MF Capstone

-- 1. Top 5 funds by AUM
SELECT scheme_name, fund_house, aum_crore
FROM fact_performance p
JOIN dim_fund f ON p.amfi_code = f.amfi_code
ORDER BY aum_crore DESC
LIMIT 5;

-- 2. Average NAV per month for a specific fund (e.g., SBI Small Cap Fund)
SELECT d.year, d.month, AVG(n.nav) as avg_nav
FROM fact_nav n
JOIN dim_date d ON n.date = d.date
JOIN dim_fund f ON n.amfi_code = f.amfi_code
WHERE f.scheme_name LIKE '%SBI Small Cap Fund%'
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 3. SIP Year-over-Year (YoY) growth comparison
-- Since we don't have YoY growth directly in our transactions, we calculate from monthly sums
WITH monthly_sip AS (
    SELECT d.year, d.month, SUM(t.amount_inr) as total_sip
    FROM fact_transactions t
    JOIN dim_date d ON t.transaction_date = d.date
    WHERE t.transaction_type = 'SIP'
    GROUP BY d.year, d.month
)
SELECT m1.year as curr_year, m1.month, m1.total_sip as curr_sip, 
       m2.total_sip as prev_sip, 
       ROUND((m1.total_sip - m2.total_sip) / m2.total_sip * 100, 2) as yoy_growth_pct
FROM monthly_sip m1
JOIN monthly_sip m2 ON m1.year = m2.year + 1 AND m1.month = m2.month;

-- 4. Transactions by State
SELECT state, COUNT(*) as txn_count, SUM(amount_inr) as total_amount
FROM fact_transactions
GROUP BY state
ORDER BY total_amount DESC;

-- 5. Funds with expense ratio < 1%
SELECT scheme_name, category, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1.0
ORDER BY expense_ratio_pct ASC;

-- 6. Best Performing Funds over 3 Years (Sharpe Ratio > 1.0)
SELECT f.scheme_name, p.return_3yr_pct, p.sharpe_ratio
FROM fact_performance p
JOIN dim_fund f ON p.amfi_code = f.amfi_code
WHERE p.sharpe_ratio > 1.0
ORDER BY p.sharpe_ratio DESC;

-- 7. Total AUM by Fund House in the latest date
SELECT fund_house, SUM(aum_crore) as total_aum
FROM fact_aum
WHERE date = (SELECT MAX(date) FROM fact_aum)
GROUP BY fund_house
ORDER BY total_aum DESC;

-- 8. Transaction amounts by Age Group and Gender
SELECT age_group, gender, SUM(amount_inr) as total_amount
FROM fact_transactions
GROUP BY age_group, gender
ORDER BY age_group, gender;

-- 9. Fund categories by average exit load
SELECT category, AVG(exit_load_pct) as avg_exit_load
FROM dim_fund
GROUP BY category
ORDER BY avg_exit_load DESC;

-- 10. Max Drawdown vs 5-Year Return Correlation insight
SELECT f.scheme_name, p.max_drawdown_pct, p.return_5yr_pct
FROM fact_performance p
JOIN dim_fund f ON p.amfi_code = f.amfi_code
ORDER BY p.max_drawdown_pct ASC;

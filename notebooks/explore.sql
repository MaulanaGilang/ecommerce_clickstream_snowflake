-- 1. size, date range, price range
SELECT COUNT(*)        AS total_rows,
       MIN(event_time) AS first_event,
       MAX(event_time) AS last_event,
       MIN(price)      AS min_price,
       MAX(price)      AS max_price
FROM 'data/raw/2019-Oct.csv';

-- 2. event mix (rows and %)
SELECT event_type,
       COUNT(*) AS rows,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM 'data/raw/2019-Oct.csv'
GROUP BY 1
ORDER BY 2 DESC;

-- 3. data quality (rows and %)
SELECT COUNT(*) FILTER (WHERE brand IS NULL)         AS null_brand,
       ROUND(100.0 * COUNT(*) FILTER (WHERE brand IS NULL) / COUNT(*), 2)         AS null_brand_pct,
       COUNT(*) FILTER (WHERE category_code IS NULL) AS null_category,
       ROUND(100.0 * COUNT(*) FILTER (WHERE category_code IS NULL) / COUNT(*), 2) AS null_category_pct,
       COUNT(*) FILTER (WHERE user_session IS NULL)  AS null_session,
       ROUND(100.0 * COUNT(*) FILTER (WHERE user_session IS NULL) / COUNT(*), 2)  AS null_session_pct,
       COUNT(*) FILTER (WHERE price <= 0)            AS bad_price,
       ROUND(100.0 * COUNT(*) FILTER (WHERE price <= 0) / COUNT(*), 2)            AS bad_price_pct
FROM 'data/raw/2019-Oct.csv';

-- 4. exact duplicate events (rows and %)
SELECT COUNT(*) - COUNT(DISTINCT (event_time, event_type, product_id, user_id, user_session)) AS duplicate_rows,
       ROUND(100.0 * (COUNT(*) - COUNT(DISTINCT (event_time, event_type, product_id, user_id, user_session))) / COUNT(*), 2) AS duplicate_pct
FROM 'data/raw/2019-Oct.csv';
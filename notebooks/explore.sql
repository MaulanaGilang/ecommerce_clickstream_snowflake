-- row count and event mix
SELECT event_type, COUNT(*) FROM 'data/raw/2019-Oct.csv' GROUP BY 1;

-- missing values
SELECT COUNT(*) FILTER (WHERE brand IS NULL)         AS null_brand,
       COUNT(*) FILTER (WHERE category_code IS NULL) AS null_category,
       COUNT(*) FILTER (WHERE user_session IS NULL)  AS null_session,
       COUNT(*) FILTER (WHERE price <= 0)            AS bad_price
FROM 'data/raw/2019-Oct.csv';

-- exact duplicate events
SELECT COUNT(*) - COUNT(DISTINCT (event_time, event_type, product_id, user_id, user_session))
FROM 'data/raw/2019-Oct.csv';

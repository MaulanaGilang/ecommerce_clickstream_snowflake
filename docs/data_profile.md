# Data profile: REES46 e-commerce events

Source: Kaggle `mkechinov/ecommerce-behavior-data-from-multi-category-store`

## Size

|             | Oct 2019            | Nov 2019            | Total   |
| ----------- | ------------------- | ------------------- | ------- |
| File size   | 8.7 GB              | 5.5 GB              | 14.7 GB |
| Rows        | 42448764            | 67501979            | 109.9M  |
| First event | 2019-10-01 00:00:00 | 2019-11-01 00:00:00 |         |
| Last event  | 2019-10-31 23:59:59 | 2019-11-30 23:59:59 |         |

## Event mix

| event_type       | Oct rows | Oct % | Nov rows | Nov % |
| ---------------- | -------- | ----- | -------- | ----- |
| view             | 40779399 | 96.07 | 63556110 | 94.15 |
| cart             | 926516   | 2.18  | 3028930  | 4.49  |
| remove_from_cart |          |       |          |       |
| purchase         | 742849   | 1.75  | 916939   | 1.36  |

## Data quality

| Issue                  | Oct rows | Oct % | Nov rows | Nov % |
| ---------------------- | -------- | ----- | -------- | ----- |
| Null brand             | 6113008  | 14.4  | 9218235  | 13.66 |
| Null category_code     | 13515609 | 31.84 | 21898171 | 32.44 |
| Null user_session      | 2        | 0.0   | 10       | 0.0   |
| Price <= 0             | 68673    | 0.16  | 188088   | 0.28  |
| Exact duplicate events | 30220    | 0.07  | 100530   | 0.15  |

## Price

|     | Oct     | Nov     |
| --- | ------- | ------- |
| Min | 0.0     | 0.0     |
| Max | 2574.07 | 2574.07 |

## Notes

- `event_time` is a string ending in " UTC"
- `category_code` is a dotted path (e.g. `electronics.smartphone`), often empty
- Duplicates are checked within each file, not across the Oct/Nov boundary
- Handling: bad rows are flagged in dbt `stg_events_checked`, not dropped

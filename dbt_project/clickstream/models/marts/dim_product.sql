select product_id, category_id, category_l1, category_l2, brand, price as last_seen_price
from {{ ref('stg_events') }}
where product_id is not null
qualify row_number() over (partition by product_id order by event_ts desc) = 1

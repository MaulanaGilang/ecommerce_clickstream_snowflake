with events as (
    select
        product_id,
        count_if(event_type = 'view')                   as views,
        count_if(event_type = 'cart')                   as carts,
        count_if(event_type = 'purchase')               as purchases,
        sum(iff(event_type = 'purchase', price, 0))     as revenue
    from {{ ref('stg_events') }}
    where product_id is not null
    group by product_id
)

select
    e.product_id,
    p.brand,
    p.category_l1,
    p.category_l2,
    e.views,
    e.carts,
    e.purchases,
    e.revenue,
    div0(e.purchases, e.views)                          as view_to_purchase_rate
from events e
join {{ ref('dim_product') }} p using (product_id)

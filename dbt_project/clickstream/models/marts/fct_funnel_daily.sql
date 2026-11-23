{{ config(materialized='incremental', incremental_strategy='delete+insert',
          unique_key='event_date') }}

select
    event_date,
    category_l1,
    count(distinct iff(event_type = 'view',     user_session, null)) as sessions_viewed,
    count(distinct iff(event_type = 'cart',     user_session, null)) as sessions_carted,
    count(distinct iff(event_type = 'purchase', user_session, null)) as sessions_purchased,
    sum(iff(event_type = 'purchase', price, 0))                       as revenue
from {{ ref('stg_events') }}
{% if is_incremental() %}
where event_date = '{{ var("run_date") }}'
{% endif %}
group by 1, 2

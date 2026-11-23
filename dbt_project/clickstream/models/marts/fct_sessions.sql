{{ config(materialized='incremental', incremental_strategy='merge',
          unique_key='user_session') }}

with events as (
    select e.*
    from {{ ref('stg_events') }} e
    {% if is_incremental() %}
    where e.user_session in (
        select user_session from {{ ref('stg_events') }}
        where event_date = '{{ var("run_date") }}'
    )
    {% endif %}
)

select
    user_session,
    min(user_id)                                        as user_id,
    min(event_ts)                                       as session_start,
    max(event_ts)                                       as session_end,
    datediff('second', min(event_ts), max(event_ts))    as duration_sec,
    count(*)                                            as events,
    count_if(event_type = 'view')                       as views,
    count_if(event_type = 'cart')                       as carts,
    count_if(event_type = 'purchase')                   as purchases,
    sum(iff(event_type = 'purchase', price, 0))         as revenue,
    count_if(event_type = 'purchase') > 0               as converted
from events
group by user_session
{{ config(materialized='incremental', incremental_strategy='delete+insert',
          unique_key='event_date') }}

with src as (
    select * from {{ source('raw', 'events') }}
    {% if is_incremental() %}
    where event_date = '{{ var("run_date") }}'
    {% endif %}
),

typed as (
    select
        try_to_timestamp_ntz(replace(event_time, ' UTC', ''))              as event_ts,
        event_date,
        lower(event_type)                                                   as event_type,
        try_to_number(product_id)                                           as product_id,
        try_to_number(category_id)                                          as category_id,
        coalesce(nullif(split_part(category_code, '.', 1), ''), 'unknown')  as category_l1,
        coalesce(nullif(split_part(category_code, '.', 2), ''), 'unknown')  as category_l2,
        coalesce(nullif(lower(brand), ''), 'unknown')                       as brand,
        try_to_double(price)                                                as price,
        try_to_number(user_id)                                              as user_id,
        nullif(user_session, '')                                            as user_session,
        _source_file,
        _loaded_at
    from src
)

select
    *,
    case
        when event_ts is null                                         then 'bad_timestamp'
        when event_type is null
          or event_type not in ('view', 'cart', 'remove_from_cart', 'purchase') then 'bad_event_type'
        when price is null or price < 0                                then 'bad_price'
        when user_id is null                                           then 'missing_user'
        when user_session is null                                      then 'missing_session'
    end as reject_reason,
    row_number() over (
        partition by event_ts, event_type, product_id, user_id, user_session
        order by _loaded_at
    ) > 1 as is_duplicate
from typed

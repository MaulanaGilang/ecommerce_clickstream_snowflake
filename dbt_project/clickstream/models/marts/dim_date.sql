with days as (
    {{ dbt_utils.date_spine(datepart="day", start_date="'2019-10-01'::date", end_date="'2019-12-01'::date") }}
)

select
    date_day::date                       as date_day,
    dayname(date_day)                    as day_name,
    dayofweekiso(date_day)               as day_of_week,   -- 1 = Monday
    dayofweekiso(date_day) in (6, 7)     as is_weekend,
    weekofyear(date_day)                 as week_of_year,
    month(date_day)                      as month
from days

with r as (select count(*) as n from {{ source('raw', 'events') }}
           where event_date = '{{ var("run_date") }}'),
     c as (select count(*) as n from {{ ref('stg_events_checked') }}
           where event_date = '{{ var("run_date") }}')
select r.n as raw_rows, c.n as checked_rows from r, c where r.n <> c.n
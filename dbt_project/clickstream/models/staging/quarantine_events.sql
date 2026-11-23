select * from {{ ref('stg_events_checked') }}
where reject_reason is not null
select * exclude (reject_reason, is_duplicate)
from {{ ref('stg_events_checked') }}
where reject_reason is null and not is_duplicate
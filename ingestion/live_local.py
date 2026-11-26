"""Step 8d: local live page for the Snowpipe demo. Never deploy this; it needs your
Snowflake key.

    streamlit run ingestion/live_local.py

Needs SNOWFLAKE_ACCOUNT and SNOWFLAKE_PRIVATE_KEY_PATH in the environment.
Screen-record it while replay_live.py runs, for the README.
"""

import os
import time

import snowflake.connector
import streamlit as st

st.set_page_config(page_title="Snowpipe live", layout="wide")
st.title("Snowpipe: rows arriving in RAW.EVENTS_LIVE")


@st.cache_resource
def connect():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user="PIPELINE_SVC",
        private_key_file=os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]),
        role="TRANSFORMER",
        warehouse="CLICKSTREAM_WH",
        database="CLICKSTREAM",
    )


cur = connect().cursor()
cur.execute(
    # _loaded_at is stored in the account's local time (US Pacific by default);
    # read it as session-local, then show it in UTC.
    "select count(*), max(event_time), count(distinct _source_file), "
    "convert_timezone('UTC', max(_loaded_at)::timestamp_ltz)::timestamp_ntz "
    "from CLICKSTREAM.RAW.EVENTS_LIVE"
)
rows, latest_event, files, last_load = cur.fetchone()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows loaded", f"{rows:,}")
c2.metric("Files loaded", files)
c3.metric("Latest event time", latest_event or "-")
c4.metric("Last load (UTC)", str(last_load or "-")[:19])

st.caption("Refreshes every 10 seconds.")
time.sleep(10)
st.rerun()

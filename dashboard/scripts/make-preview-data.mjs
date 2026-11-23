// Generates PREVIEW data shaped like the pipeline's Snowflake mart exports.
// Deterministic (seeded) so the site never changes between builds.
// Replace by running the real export (dashboard/export.py) after the
// backfill, writing the same files with "preview": false in meta.json.
//
//   node scripts/make-preview-data.mjs

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "data");
mkdirSync(OUT, { recursive: true });

// mulberry32
let seed = 20191001;
const rand = () => {
  seed |= 0;
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const jitter = (spread) => 1 + (rand() * 2 - 1) * spread;
const round = (n) => Math.round(n);

// ---- calendar: 2019-10-01 .. 2019-11-30 (61 days) ----
const days = [];
for (let d = new Date(Date.UTC(2019, 9, 1)); d <= new Date(Date.UTC(2019, 10, 30)); d.setUTCDate(d.getUTCDate() + 1)) {
  days.push(new Date(d));
}
const iso = (d) => d.toISOString().slice(0, 10);

// Raw event totals published with the dataset (Oct + Nov 2019)
const RAW_OCT = 42_448_764;
const RAW_NOV = 67_501_979;

// day-level volume shape: Nov busier, mid-November sale spike, mild weekly cycle
const dayWeight = days.map((d) => {
  const m = d.getUTCMonth();
  const dom = d.getUTCDate();
  const dow = d.getUTCDay();
  let w = m === 9 ? 1 : 1.42;
  if (m === 10 && dom >= 15 && dom <= 17) w *= [1.9, 2.6, 2.3][dom - 15];
  if (m === 10 && dom === 14) w *= 1.25;
  w *= [0.94, 1.03, 1.02, 1.0, 1.0, 0.97, 0.92][dow];
  return w * jitter(0.04);
});
const sumMonth = (m) => dayWeight.reduce((s, w, i) => (days[i].getUTCMonth() === m ? s + w : s), 0);
const octSum = sumMonth(9);
const novSum = sumMonth(10);
const eventsByDay = dayWeight.map((w, i) =>
  round(days[i].getUTCMonth() === 9 ? (RAW_OCT * w) / octSum : (RAW_NOV * w) / novSum),
);
// fix rounding so totals match exactly
const fix = (m, target) => {
  const idx = days.findIndex((d) => d.getUTCMonth() === m);
  const got = eventsByDay.reduce((s, v, i) => (days[i].getUTCMonth() === m ? s + v : s), 0);
  eventsByDay[idx] += target - got;
};
fix(9, RAW_OCT);
fix(10, RAW_NOV);

// ---- data quality (dbt stg_events_checked) ----
// RAW keeps every column as text; dbt flags each row as clean, quarantined
// (with a reject_reason) or an exact duplicate. Zero prices are valid; only
// negative or unparseable prices are rejected.
const quality = days.map((d, i) => {
  const raw = eventsByDay[i];
  const bad_timestamp = 0;
  const bad_event_type = 0;
  const bad_price = round(raw * 0.0000012 * jitter(0.9));
  const missing_user = 0;
  const missing_session = round(raw * 0.0000031 * jitter(0.8));
  const quarantined = bad_timestamp + bad_event_type + bad_price + missing_user + missing_session;
  const duplicates = round(raw * 0.0041 * jitter(0.3));
  return {
    event_date: iso(d),
    raw_rows: raw,
    clean_rows: raw - quarantined - duplicates,
    quarantined,
    duplicates,
    reasons: { bad_timestamp, bad_event_type, bad_price, missing_user, missing_session },
  };
});

// ---- categories (category_l1) ----
// share of sessions, view->cart rate, cart->purchase rate, avg purchase price
const CATS = [
  ["electronics", 0.36, 0.118, 0.63, 318],
  ["unknown", 0.17, 0.071, 0.57, 142],
  ["appliances", 0.13, 0.092, 0.56, 211],
  ["computers", 0.085, 0.058, 0.49, 487],
  ["apparel", 0.082, 0.026, 0.41, 64],
  ["furniture", 0.05, 0.034, 0.39, 186],
  ["construction", 0.04, 0.061, 0.53, 97],
  ["kids", 0.031, 0.052, 0.47, 88],
  ["auto", 0.027, 0.049, 0.51, 121],
  ["accessories", 0.02, 0.038, 0.43, 47],
  ["sport", 0.015, 0.031, 0.42, 133],
];
const catShareTotal = CATS.reduce((s, c) => s + c[1], 0);

// sessions per event ~ 1 / 4.8
const funnelDaily = [];
days.forEach((d, i) => {
  const sessions = eventsByDay[i] / 4.8;
  // the sale spike lifts conversion more than traffic
  const dom = d.getUTCDate();
  const spike = d.getUTCMonth() === 10 && dom >= 15 && dom <= 17 ? 1.22 : 1;
  for (const [cat, share, v2c, c2p] of CATS) {
    const viewed = round((sessions * share * jitter(0.06)) / catShareTotal);
    const carted = round(viewed * v2c * spike * jitter(0.07));
    const purchased = round(carted * Math.min(0.92, c2p * jitter(0.05)));
    funnelDaily.push({
      event_date: iso(d),
      category_l1: cat,
      sessions_viewed: viewed,
      sessions_carted: carted,
      sessions_purchased: purchased,
    });
  }
});

const categories = CATS.map(([cat, , , , price]) => {
  const rows = funnelDaily.filter((r) => r.category_l1 === cat);
  const viewed = rows.reduce((s, r) => s + r.sessions_viewed, 0);
  const carted = rows.reduce((s, r) => s + r.sessions_carted, 0);
  const purchased = rows.reduce((s, r) => s + r.sessions_purchased, 0);
  return {
    category_l1: cat,
    sessions_viewed: viewed,
    sessions_carted: carted,
    sessions_purchased: purchased,
    revenue: round(purchased * price * 1.08 * jitter(0.03)),
  };
});

// ---- price bands ----
const BANDS = [
  ["< $25", 0.17, 0.055],
  ["$25-50", 0.14, 0.061],
  ["$50-100", 0.17, 0.057],
  ["$100-250", 0.21, 0.052],
  ["$250-500", 0.15, 0.047],
  ["$500-1k", 0.1, 0.039],
  ["> $1k", 0.06, 0.024],
];
const totalViewed = categories.reduce((s, c) => s + c.sessions_viewed, 0);
const priceBands = BANDS.map(([band, share, conv]) => {
  const viewed = round(totalViewed * share * jitter(0.03));
  return { price_band: band, sessions_viewed: viewed, sessions_purchased: round(viewed * conv * jitter(0.04)) };
});

// ---- brands (top by purchases) ----
const BRANDS = [
  ["samsung", 0.105, 0.081],
  ["apple", 0.088, 0.079],
  ["xiaomi", 0.071, 0.058],
  ["huawei", 0.024, 0.066],
  ["lucente", 0.009, 0.071],
  ["cordiant", 0.008, 0.083],
  ["lg", 0.017, 0.049],
  ["oppo", 0.012, 0.052],
  ["sony", 0.013, 0.044],
  ["acer", 0.011, 0.047],
  ["artel", 0.007, 0.06],
  ["elenberg", 0.006, 0.055],
];
const brands = BRANDS.map(([brand, share, conv]) => {
  const viewed = round(totalViewed * share * jitter(0.05));
  const purchased = round(viewed * conv * jitter(0.05));
  return { brand, sessions_viewed: viewed, sessions_purchased: purchased };
}).sort((a, b) => b.sessions_purchased - a.sessions_purchased);

// ---- cart abandonment by hour (UTC) x weekday ----
const hourly = [];
for (let dow = 0; dow < 7; dow++) {
  for (let h = 0; h < 24; h++) {
    // activity peaks ~ 14-17 UTC; abandonment highest overnight
    const activity = 0.25 + 0.75 * Math.exp(-((h - 15.5) ** 2) / 30);
    const abandon = 0.36 + 0.14 * (1 - activity) + (dow === 0 || dow === 6 ? 0.025 : 0);
    const carted = round(28_000 * activity * (dow === 0 ? 0.92 : 1) * jitter(0.05));
    hourly.push({
      weekday: dow,
      hour: h,
      sessions_carted: carted,
      sessions_abandoned: round(carted * Math.min(0.9, abandon * jitter(0.04))),
    });
  }
}

// ---- Airflow runs (one per day): upload_to_s3 >> copy_into_raw >> dbt_build ----
const runs = days.map((d, i) => {
  const k = eventsByDay[i] / 1_500_000;
  const upload = round((9 + 6 * k) * jitter(0.2));
  const copy = round((14 + 11 * k) * jitter(0.15));
  const dbt = round((62 + 38 * k) * jitter(0.12));
  return { ds: iso(d), upload_s: upload, copy_s: copy, dbt_s: dbt, state: "success", tries: 1 };
});
// one run needed Airflow's automatic retry (retries=2 in the DAG)
runs[23].tries = 2;
runs[23].copy_s += 120;

// XS warehouse ~ 1 credit per running hour, billed per second, plus setup and testing
const warehouseSeconds = runs.reduce((s, r) => s + r.copy_s + r.dbt_s, 0);
const credits_used = Math.round((warehouseSeconds / 3600 + 1.6) * 10) / 10;

// ---- Snowpipe demo: one Parquet file per minute of event time, 10 s apart ----
const REPLAY_DAY = "2019-11-30";
const replayEvents = eventsByDay[days.findIndex((d) => iso(d) === REPLAY_DAY)];
const START_MINUTE = 12 * 60;
const FILES = 150; // 25 minutes of wall-clock demo
const GAP_S = 10;
const perMinute = (m) => {
  const h = m / 60;
  return (0.18 + Math.exp(-((h - 15) ** 2) / 26) + 0.35 * Math.exp(-((h - 7) ** 2) / 6)) * jitter(0.09);
};
let shapeSum = 0;
for (let m = 0; m < 1440; m++) shapeSum += perMinute(m);
const snowpipe = Array.from({ length: FILES }, (_, i) => {
  const minute = START_MINUTE + i;
  const rows = round((replayEvents * perMinute(minute)) / shapeSum);
  const sent_s = i * GAP_S;
  // pipe latency: mostly 30-60 s, an occasional slow file
  const latency_s = round(26 + 22 * rand() + (rand() < 0.06 ? 30 * rand() : 0));
  return {
    file: `live/${REPLAY_DAY}/${String(Math.floor(minute / 60)).padStart(2, "0")}${String(minute % 60).padStart(2, "0")}.parquet`,
    rows,
    sent_s,
    loaded_s: sent_s + latency_s,
    latency_s,
  };
});
const latencies = snowpipe.map((f) => f.latency_s).sort((a, b) => a - b);
const snowpipe_median_latency_s = latencies[Math.floor(latencies.length / 2)];

// ---- headline totals ----
const sum = (arr, k) => arr.reduce((s, r) => s + r[k], 0);
const totals = {
  raw_events: RAW_OCT + RAW_NOV,
  raw_csv_gb: 14.7,
  parquet_gb: 2.1,
  days: days.length,
  raw_rows: sum(quality, "raw_rows"),
  clean_rows: sum(quality, "clean_rows"),
  quarantined: sum(quality, "quarantined"),
  duplicates: sum(quality, "duplicates"),
  sessions_viewed: sum(categories, "sessions_viewed"),
  sessions_carted: sum(categories, "sessions_carted"),
  sessions_purchased: sum(categories, "sessions_purchased"),
  revenue: sum(categories, "revenue"),
  dbt_models: 8,
  dbt_tests: 12,
  backfill_minutes: round(runs.reduce((s, r) => s + r.upload_s + r.copy_s + r.dbt_s, 0) / 60),
  credits_used,
  credit_cap: 40,
  snowpipe_files: FILES,
  snowpipe_median_latency_s,
};

const write = (name, data) => writeFileSync(join(OUT, `${name}.json`), JSON.stringify(data));
write("meta", {
  preview: true,
  note: "Synthetic preview shaped like the Snowflake mart exports. Raw event totals are the dataset's published counts.",
  source: "REES46 eCommerce behavior data, multi-category store, Oct-Nov 2019",
  replay_day: REPLAY_DAY,
});
write("totals", totals);
write("funnel_daily", funnelDaily);
write("categories", categories);
write("price_bands", priceBands);
write("brands", brands);
write("hourly_abandonment", hourly);
write("quality_daily", quality);
write("airflow_runs", runs);
write("snowpipe_files", snowpipe);

console.log("wrote preview data to", OUT);
console.table(totals);

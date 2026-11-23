const int = new Intl.NumberFormat("en-US");

export const fmtInt = (n: number) => int.format(Math.round(n));

/** 109950743 -> "110M", 1913293 -> "1.91M", 161736 -> "162K" */
export function fmtCompact(n: number) {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `${trim(n / 1e9)}B`;
  if (abs >= 1e6) return `${trim(n / 1e6)}M`;
  if (abs >= 1e3) return `${trim(n / 1e3)}K`;
  return String(Math.round(n));
}

function trim(v: number) {
  const digits = Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2;
  return v.toFixed(digits).replace(/\.?0+$/, "");
}

export const fmtPct = (r: number, digits = 1) => `${(r * 100).toFixed(digits)}%`;

export const fmtUsd = (n: number) => `$${fmtCompact(n)}`;

export function fmtDay(iso: string) {
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

export function fmtDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

// Type contract for the consolidated bundle produced by tools/build_dashboard_data.py.

export interface Metric {
  n: number;
  rmse: number;
  mae: number;
  bias: number;
}

export interface SampleMetrics {
  all: Metric;
  ex_2020: Metric;
}

export interface HeadlineRow {
  period: string;
  advance_date: string;
  gdp_advance: number;
  headline_nowcast: number;
  error: number;
  abs_error: number;
}

export interface WeeklyRow {
  vintage: string;
  y_old: number;
  y_new: number;
  error: number;
  impact_revisions: number;
  impact_releases: number;
}

export interface DMCell {
  dm_stat: number;
  p_value: number;
  df: number;
  n: number;
  mean_loss_diff: number;
  horizon: number;
}

export interface DMSample {
  squared: DMCell;
  absolute: DMCell;
}

export interface DMResult {
  all: DMSample;
  ex_2020: DMSample;
}

export interface PerQuarterComp {
  period: string;
  fiscal_error: number;
  baseline_error: number;
  abs_error_delta: number;
  covid: boolean;
}

export interface LeakScan {
  source: string;
  quarters: number;
  advance_day_leak_nonzero: number;
  window_leak_nonzero: number;
  clean_quarters: string[];
  q2025q1_advance_day_coreleases: string[];
  q2025q1_window_coreleases: number;
}

export interface MDELeaf {
  n: number;
  df: number;
  mean_loss_diff: number;
  sd_diff: number;
  se: number;
  t_crit: number;
  t_power: number;
  sig_threshold_effect: number;
  mde: number;
  powered: boolean;
  paired_t: number;
  dm_stat: number;
  mse_base: number;
  rmse_base: number;
  sig_threshold_effect_rmse: number;
  mde_rmse: number;
}

export interface PowerMDE {
  method: string;
  alpha: number;
  power: number;
  by_sample: {
    all: { squared: MDELeaf; absolute: MDELeaf };
    ex_2020: { squared: MDELeaf; absolute: MDELeaf };
  };
}

export interface BenchPerQuarter {
  period: string;
  gdp_advance: number;
  covid: boolean;
  cutoff: string;
  dfm_error: number;
  mean_nowcast: number;
  mean_error: number;
  rw_nowcast: number;
  rw_error: number;
  ar1_nowcast: number;
  ar1_error: number;
  arma11_nowcast: number;
  arma11_error: number;
}

export interface Finding {
  id: string;
  title: string;
  body: string;
  evidence: Record<string, unknown>;
}

export interface Dashboard {
  meta: {
    generated_from: string[];
    periods: string[];
    covid_periods: string[];
    n_quarters: number;
    n_ex_2020: number;
    target_definition: string;
    clean_quarters: string[];
    panel_baseline: string;
    panel_fiscal: string;
  };
  headline: { baseline: HeadlineRow[]; fiscal: HeadlineRow[] };
  metrics: { baseline: SampleMetrics; fiscal: SampleMetrics };
  weekly: {
    baseline: Record<string, WeeklyRow[]>;
    fiscal: Record<string, WeeklyRow[]>;
  };
  skipped: {
    baseline: Record<string, string[]>;
    fiscal: Record<string, string[]>;
  };
  comparison: {
    convention: string;
    diebold_mariano: DMResult;
    power_mde: PowerMDE;
    per_quarter: PerQuarterComp[];
    leak_scan: LeakScan;
  };
  benchmarks: {
    convention: string;
    models: string[];
    panel: string;
    metrics: Record<string, SampleMetrics>;
    diebold_mariano: Record<string, DMResult>;
    per_quarter: BenchPerQuarter[];
    gdpnow_note: string;
  };
  findings: Finding[];
}

export type Variant = "baseline" | "fiscal";

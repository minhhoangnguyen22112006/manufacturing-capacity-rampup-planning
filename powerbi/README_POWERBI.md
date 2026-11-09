# Power BI Desktop — native dashboard build guide

This package contains **ready-to-import CSV tables, validated metrics, a DAX measures file and a finished offline interactive HTML dashboard**. A native `.pbix` was **not generated**, because Power BI Desktop is not available in this execution environment. You can recreate its visual pages directly from the provided tables.

## 1. Import

Open Power BI Desktop → **Get Data → Text/CSV**. Import these from `outputs/`:

- `dim_week.csv`, `dim_product.csv`, `dim_stage.csv`, `dim_machine.csv`, `dim_scenario.csv`
- `actual_week_product.csv`, `actual_week_stage.csv`, `actual_wip.csv`, `actual_machine_week.csv`
- `sim_service.csv`, `sim_production.csv`, `sim_wip.csv`, `sim_capacity.csv`
- `stress_summary.csv`, `scenario_summary.csv` (optional; `scenario_summary.csv` duplicates `dim_scenario`)

Load each as a separate table, with table names equal to their filenames (without `.csv`). Select `week_id` and `stage_id` as **Whole number**, other values as Decimal number, and `week_start`, `week_end` as Date. `scenario` is Text; `machine_id` and `product_id` are Text.

You can alternatively import the SQLite database using a compatible SQLite ODBC connector, but the provided CSV approach is simpler and guaranteed to reproduce the precomputed outputs.

## 2. Relationship diagram (single direction, one-to-many)

- `dim_week[week_id]` → every actual/sim weekly fact's `[week_id]`.
- `dim_product[product_id]` → `actual_week_product`, `actual_wip`, `sim_service`, `sim_production`, `sim_wip`, `actual_stage_product` (if imported).
- `dim_stage[stage_id]` → `actual_week_stage[stage_id]`, `actual_wip[after_stage_id]`, `sim_production[stage_id]`, `sim_capacity[stage_id]`, `sim_wip[after_stage_id]`, `actual_machine_week[stage_id]`.
- `dim_scenario[scenario]` → all `sim_*` facts' `[scenario]`.
- `dim_machine[machine_id]` → `actual_machine_week[machine_id]`, `sim_production[machine_id]`, `sim_capacity[machine_id]`.

**Avoid ambiguous paths:** Do *not* also connect `dim_stage` to `dim_machine` if you use direct stage-to-fact relationships. Keep single direction from dimension to facts. Do not link `sim_*` to actual tables directly. The `dim_machine` table does not include the new hypothetical machine `M0205_SCENARIO`, so its fact rows will not be filterable by `dim_machine` until that row is added. If building a full machine-detail page, append this hypothetical machine to a copied machine dimension or exclude it with an explicit caveat.

## 3. Measures

Create Power BI measures from `MEASURES.dax` individually. Format percentage measures as `0.0%` (the DAX returns decimals such as 0.9907), and cost as `$#,0`. Never sum **ending backlog or ending inventory across weeks**, because they are stock measures; choose last visible week.

## 4. Recommended report pages

### Page 1 — Supplier Executive Overview
Cards: `Actual Demand Units`, `Actual Shipped Units`, `Actual Fill Rate %`, `Actual Ending Unfulfilled Units`, `Actual Ending WIP Units`.
Line chart: week_id vs actual Demand/Shipped, and Actual Final Finished Output. Slicer: product. Line/area WIP by `after_stage_id`.

### Page 2 — Capacity and Bottleneck
Heatmap/matrix: week_id columns, stage name rows, conditional background using Actual Nominal Capacity Load %. Line chart: Actual Stage Yield %. Bar chart: machine-week ideal workload and effective minutes. Add commissioning markers W9 (M0304 Polishing) and W13 (M0404 Inspection).

### Page 3 — Investment & What-if Scenarios
Slicer `dim_scenario[scenario]` in single-select mode. Cards: `Sim Total Shipped`, `Sim Fulfillment %`, `Sim Ending Backlog`, `Scenario Total Policy Cost (Assumed USD)`. Chart: line `sim_service[week_id]` vs `Sim Ending Backlog`; bars: `dim_scenario[scenario]` vs ending_backlog and total_policy_cost_usd_assumed. A scenario table with capex, performance, OT and backlog penalties.

### Page 4 — Risk & Data Quality
Bars: `stress_summary[scenario]` vs probability_zero_backlog. Table: WIP reconciliation_delta and FG reconciliation_delta; data-quality warning that daily snapshot finished_goods_units is zero even when ledger calculation is positive. Explain perfect-hindsight/look-ahead limitation.

## 5. Dataset provenance and filter caution

- All raw rows are **synthetic** and were generated for this case study, not Apple operations.
- Actual finished stage throughput differs from actual shipments because opening FG inventory = 4,200 units.
- Actual order units not fulfilled = 7,816; all recorded shipment rows are on/before order due date. Unfulfilled is not equivalent to shipped late.
- LP scenarios use future-realized demand, yield and downtime within the historical 16-week horizon. They are hindsight counterfactuals, **not future forecasts**.
- Stress experiments also optimize each realized perturbation path with hindsight. Their zero-backlog probabilities are optimistic exploratory sensitivity checks, not calibrated future OTIF probabilities.
- Cost inputs in scenario analysis are illustrative and should not be quoted as manufacturer audited costs. Scenarios were solved for maximum service, then costs compared **post-hoc**, not selected by a global cost-minimizing MILP.

## 6. Optional Page 5 — Forward planning W17–W24

For a future-looking page, also import:
- `forward_demand_forecast_W17_W24.csv` (rename `forward_demand_forecast_W17_W24`),
- `forward_service_W17_W24.csv`, `forward_capacity_W17_W24.csv`,
- `forward_scenario_summary_W17_W24.csv`, `dim_future_scenario.csv`,
- **`dim_week_extended.csv`** (use this **in place of** the 16-week `dim_week.csv` if you want a single time dimension W1–W24; rename this imported table `dim_week`).

Relate `dim_future_scenario[scenario]` to `forward_service_W17_W24[scenario]` and `forward_capacity_W17_W24[scenario]`. Relate the extended dim_week by week_id and the usual product/stage dimensions to the corresponding future facts. To avoid ambiguity, leave `forward_scenario_summary_W17_W24` as a standalone comparison table or connect to dim_future_scenario with a single-direction relationship.

Charts: W1–W16 actual demand vs W17–W24 trend forecast (dashed), W17–W24 end backlog by scenario, stage effective load at W24, and a total forecast-vs-shipped bar. Slicer: `dim_future_scenario[scenario]`. The forecast is a simple extrapolation and is not comparable to observed orders as fact. In W24 F3, Polishing becomes 100%-loaded; a new Cutting machine has no incremental output benefit over the equivalent plan without that machine.

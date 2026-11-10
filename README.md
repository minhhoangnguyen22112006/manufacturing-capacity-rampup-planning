# Manufacturing Capacity & Ramp-Up Optimization

**Manufacturing Operations & Supply Management Analytics | SQL Server · Python · Linear Programming · Capacity Planning · Stress Testing · Power BI-ready Data**

An independent, end-to-end manufacturing analytics portfolio project examining production bottlenecks, capacity utilization, material flow, and operational strategies for improving customer demand fulfillment.

**Industry Context:** Precision Component Manufacturing  
**Historical Analysis:** January–April 2026 (16 weeks)  
**Forward Planning:** Weeks 17–24 (8 weeks)  
**Project Type:** Independent Portfolio Case Study  
**Data Source:** 100% Synthetic

> **Data Disclaimer:** This project uses entirely synthetic manufacturing data. It is not affiliated with Apple, and no proprietary Apple manufacturing or supplier information is used. All optimization improvements, capacity scenarios, and financial estimates are modeled outcomes, not realized factory performance or cost savings.

---

## 1. Executive Summary

### Business Problem

Manufacturing companies must balance customer demand, equipment capacity, production efficiency, and operational costs while maintaining reliable delivery performance.

This project examines a simulated four-stage manufacturing line:

**Precision Cutting → Edge Grinding → Surface Polishing → Optical Inspection**

The analysis addresses four business questions:

1. Which production stages constrain overall manufacturing throughput?
2. How can production allocation and material flow be optimized without immediately investing in new equipment?
3. Which operational interventions offer the best trade-off between demand fulfillment and incremental cost?
4. How might bottlenecks shift as production capacity changes during a future ramp-up?

### Dataset Overview

| Component | Description |
|---|---|
| Historical Period | 16 weeks (January–April 2026) |
| Production Stages | 4 sequential stages |
| Products | P01 and P02 |
| Production Schedule | 2 shifts per day |
| Shift Duration | 480 minutes |
| Data | Production, capacity, downtime, demand, shipments, and WIP |
| Analytical Methods | SQL, Linear Programming, Scenario Analysis, Stress Testing |
| Historical Capacity Policies | 6 scenarios (S0–S5) |
| Stress Testing | 150 sampled scenarios across 4 policies (600 LP solves) |
| Forward Planning | Weeks 17–24 |

### Key Findings

| KPI | Result |
|---|---:|
| Historical Customer Demand | 842,905 units |
| Historical Shipments | 835,089 units |
| Historical Order Fill Rate | 99.07% |
| Historical Unfulfilled Demand at W16 | 7,816 units |
| Finished Output at Inspection | 830,889 units |
| Opening Finished Goods Inventory | 4,200 units |
| Accumulated WIP Before Grinding at W16 | 117,938 units |
| Optimized Backlog Without New Equipment | 4,469 units |
| Simulated Backlog Reduction | 42.8% |

The historical production system fulfilled **99.07% of customer demand**, but accumulated significant inter-stage WIP and ended Week 16 with 7,816 unfulfilled units.

A deterministic linear programming model reduced simulated end-period backlog to 4,469 units without adding equipment, demonstrating opportunities to improve production allocation and material flow.

### Recommended Operational Decision

Six historical capacity scenarios were evaluated using deterministic linear programming.

Under the model's idealized planning assumptions, three intervention types achieved zero simulated end-period backlog:

- Targeted overtime at Cutting and Grinding.
- A 5-percentage-point performance improvement.
- Additional Grinding equipment.

**Recommended historical counterfactual: up to 10% targeted overtime at Cutting and Grinding, starting in Week 9.**

| Decision KPI | Result |
|---|---:|
| Modeled Demand Fulfillment | 100% |
| Simulated End-Period Backlog | 0 units |
| Historical Unfulfilled Demand | 7,816 units |
| Assumed Incremental Overtime Cost | Approximately $1.3K |
| Additional Equipment Required | None |

The recommendation favors a targeted operational intervention before major capital expenditure, subject to overtime feasibility, workforce availability, and the stated cost assumptions.

**These are counterfactual simulation results, not realized manufacturing improvements.**

### Business Implications

The analysis highlights three operational lessons:

1. **Capacity utilization alone is not sufficient:** Production decisions should account for material flow, inter-stage WIP, and overall line throughput.
2. **Targeted interventions can outperform broad capacity expansion:** Improving constrained stages may provide better modeled results than increasing equipment capacity indiscriminately.
3. **Bottlenecks are dynamic:** Expanding one stage can shift the production constraint downstream.

---

## 2. Manufacturing Process & Bottleneck Analysis

### Production Flow

The simulated manufacturing line consists of four sequential stages:

| Stage | Manufacturing Process | Operational Focus |
|---|---|---|
| 1 | Precision Cutting | Material preparation and initial throughput |
| 2 | Edge Grinding | Intermediate processing and WIP accumulation |
| 3 | Surface Polishing | Finishing capacity and downstream flow |
| 4 | Optical Inspection | Final quality acceptance and finished output |

Each stage operates under machine availability, planned and unplanned downtime, performance factors, and quality yield assumptions.

### Historical Bottleneck: Edge Grinding

During Weeks 1–16, Edge Grinding was identified as a primary flow constraint.

By Week 16, **117,938 units of WIP had accumulated immediately upstream of Grinding**, indicating a significant imbalance between incoming material flow and downstream processing.

This finding should be interpreted alongside stage-level capacity utilization, processing throughput, and weekly WIP trends. WIP accumulation alone does not establish a unique bottleneck.

The historical analysis focuses on:

- Stage-level available and effective capacity.
- Machine performance and downtime.
- Production throughput.
- Inter-stage WIP accumulation.
- Customer demand and unfulfilled orders.

### Forward-Looking Bottleneck Migration

The forward planning model demonstrates that bottlenecks may change when equipment capacity is expanded.

Under tested scenarios that increase Grinding capacity, Surface Polishing becomes a projected downstream constraint, reaching approximately **100% modeled load**.

Adding Cutting capacity on top of Grinding expansion does not improve overall results in the tested configuration.

**Key insight:** Equipment investments should be evaluated across the entire production chain, rather than optimizing individual stages in isolation.

---

## 3. Data Preparation & SQL Analysis

### Objective

Build a reproducible analytical foundation for evaluating production performance, material flow, capacity constraints, and customer demand fulfillment.

### Data Preparation

The project includes SQL-based analysis and Python processing of manufacturing data.

Key data elements include:

- Production dates, machines, shifts, and products.
- Input units, good units, and scrap units.
- Scheduled production minutes.
- Planned and unplanned downtime.
- Machine performance factors.
- Customer orders and shipments.
- Stage-level capacity and WIP.

The analytical workflow supports:

- Data validation and consistency checks.
- Production throughput analysis.
- Capacity and utilization calculations.
- WIP reconciliation.
- Shipment and backlog analysis.

### SQL Implementation

Two SQL workflows are provided:

**SQL Server / T-SQL**

`sql/02_sqlserver_ssms.sql`

Contains SQL Server-oriented manufacturing analysis queries intended for the project's staging and cleaned schemas.

**SQLite Reproduction**

`sql/01_sqlite_reproduce.sql`

Provides a portable way to reproduce relevant analyses using the included SQLite database without requiring SQL Server.

The SQLite workflow improves reproducibility; it does not replace the SQL Server-specific analytical scripts.

---

## 4. Production Allocation Optimization

### Optimization Objective

A Python-based deterministic linear programming model evaluates production allocation and material flow under manufacturing constraints.

The model aims to improve customer demand fulfillment while respecting the assumed operating capacity and sequential manufacturing process.

### Operational Constraints

The optimization considers:

- Available stage capacity.
- Sequential material flow.
- Production and inventory balance.
- Customer demand.
- Product allocation.
- Capacity intervention assumptions.

### Baseline Optimization Result

| Metric | Historical Observed | Optimized Counterfactual |
|---|---:|---:|
| End-Period Unfulfilled Demand | 7,816 units | 4,469 units |
| Reduction vs. Historical | — | 42.8% |
| Additional Equipment | — | None |

The optimized counterfactual reduces end-period backlog by approximately **42.8%** without requiring additional equipment.

This result reflects a perfect-hindsight replay of historical conditions. It should not be interpreted as an operational improvement achieved during the original production period.

---

## 5. Capacity Scenario Evaluation

### Scenario Design

The project evaluates six capacity policies, labeled S0–S5 in the Python scenario framework.

The tested interventions include:

- Baseline or as-is production allocation.
- Targeted overtime.
- Machine performance improvements.
- Additional equipment capacity.
- Alternative combinations of capacity interventions.

The scenarios assess how changes in effective capacity affect production flow and end-period demand fulfillment.

### Key Scenario Findings

| Intervention | Modeled W16 Backlog | Interpretation |
|---|---:|---|
| Optimized as-is production allocation | 4,469 units | Improvement without equipment investment |
| Up to 10% overtime at Cutting and Grinding from W9 | 0 units | Eliminates modeled backlog |
| Performance improvement of 5 percentage points from W9 | 0 units | Eliminates modeled backlog |
| One additional Grinding machine from W9 | 0 units | Eliminates modeled backlog |

The remaining policies and detailed scenario identifiers are available in the Python outputs and project report.

### Cost Considerations

The recommended targeted overtime policy is associated with approximately **$1.3K in assumed incremental overtime cost**.

The estimate depends on modeled overtime rates, machine-hours, and scenario assumptions.

It is not a verified payroll expense or realized operating cost.

The comparison illustrates how a relatively small operational intervention may improve modeled demand fulfillment without immediate equipment investment.

However, equipment expansion and performance improvement policies may have different implementation costs, lead times, workforce requirements, and operational risks.

---

## 6. Robustness & Stress Testing

### Objective

Evaluate whether capacity strategies remain effective when operational conditions differ from the deterministic baseline assumptions.

### Stress-Test Design

The project includes:

- **150 sampled operational scenarios**
- **4 evaluated capacity policies**
- **600 linear programming solves**

The analysis tests policy performance across varying operating conditions.

### Analytical Purpose

Stress testing supports:

- Comparison of alternative capacity policies.
- Assessment of sensitivity to uncertain operating assumptions.
- Identification of policies that may be vulnerable to production variability.
- Evaluation of the robustness of operational recommendations.

The stress tests extend the analysis beyond a single deterministic optimization run.

**Interpretation limitation:** These results are scenario-based sensitivity analyses. They are not statistically validated predictions of future factory performance, and their interpretation depends on the underlying sampling and uncertainty assumptions.

See `python/stress_test.py` and the project outputs for implementation details.

---

## 7. Forward-Looking Capacity Planning: Weeks 17–24

### Why Extend the Analysis?

Historical optimization identifies missed opportunities in past production performance.

However, real manufacturing decisions must be made using information available before production occurs.

To address this limitation, the project includes an illustrative forward-looking capacity planning exercise.

### Forecasting Approach

The forward model:

- Uses observed demand from Weeks 9–16.
- Applies simple product-level linear demand trends.
- Carries actual Week 16 inventory and backlog into Week 17.
- Evaluates equipment and overtime interventions.
- Assumes a three-week equipment purchase lead time.

The resulting forecast is illustrative, not validated customer demand.

### Forecast Demand

| Metric | Result |
|---|---:|
| Planning Horizon | Weeks 17–24 |
| Forecast Demand | Approximately 607,573 units |
| Opening Customer Backlog | 7,816 units |
| Baseline Forward Scenario Backlog at W24 | Approximately 195,382 units |
| Tested OT + Grinding Scenario Backlog at W24 | Approximately 134,091 units |

### Forward Scenario Findings

The tested forward scenarios reduce projected backlog but do not eliminate it.

Increasing Grinding capacity improves the flow of material through the constrained stage, but can shift the bottleneck to Surface Polishing.

In the tested configuration, adding a Cutting machine on top of Grinding expansion provides no further improvement.

### Operational Interpretation

The forward results demonstrate that:

- Historical improvements do not guarantee future demand fulfillment.
- Equipment expansion may create downstream capacity constraints.
- Capacity planning should account for bottleneck migration.
- A full-line evaluation is necessary before approving capital expenditure.

**Limitation:** The forward model uses illustrative demand forecasts and assumed equipment lead times. It should not be used to approve real manufacturing investments without additional validation.

---

## 8. Dashboard & Visualization

The repository includes an interactive HTML dashboard and Power BI-ready analytical outputs.

### Available Visualization Assets

| Asset | Description |
|---|---|
| `outputs/dashboard.html` | Interactive manufacturing analytics dashboard |
| `outputs/*.csv` | Analytical outputs for reporting |
| `powerbi/README_POWERBI.md` | Power BI data import and modeling instructions |
| `powerbi/MEASURES.dax` | Reference DAX measures |
| `figures/` | Static dashboard preview |
| `notebooks/Apple_GSM_Manufacturing_Case.ipynb` | Executed analytical notebook |

The dashboard covers historical manufacturing performance, optimization results, scenario analysis, and forward-looking planning.

### Power BI Status

The repository provides Power BI-ready datasets, model guidance, and DAX measures.

A native Power BI `.pbix` workbook is not currently included.

The HTML dashboard is a separate interactive visualization and should not be described as a Power BI workbook.

---

## 9. Reproducing the Project

### Requirements

- Python 3.10 or later
- Required Python packages listed in `requirements.txt`
- VS Code or another Python-compatible development environment
- SQL Server (optional)
- Power BI Desktop (optional)

### Quick Start

1. Read `START_HERE_VI.md` for the introductory project guide.
2. Open `outputs/dashboard.html` in Chrome or Edge.
3. Open `notebooks/Apple_GSM_Manufacturing_Case.ipynb` to inspect the executed analysis.
4. Read `PROJECT_REPORT_VI.md` for detailed business logic, results, assumptions, and limitations.

### Reproduce the Python Outputs

From the project root:

```bash
pip install -r requirements.txt

python python/run_project.py
python python/forward_plan.py
python python/stress_test.py
python python/build_dashboard.py
```

The stress-testing script is more computationally intensive because it evaluates 150 scenarios across four policies, requiring 600 LP solves.

Precomputed outputs are available for reviewing the project without rerunning every scenario.

### SQL Analysis

For a portable workflow, use:

`sql/01_sqlite_reproduce.sql`

For SQL Server, use:

`sql/02_sqlserver_ssms.sql`

The SQL Server queries may require adjustment to match the target database's staging and cleaned schemas.

### Power BI

Import the prepared CSV files into Power BI Desktop and follow:

- `powerbi/README_POWERBI.md`
- `powerbi/MEASURES.dax`

---

## 10. Repository Structure

| Directory / File | Description |
|---|---|
| `data/` | Source SQLite manufacturing database |
| `sql/` | SQL Server and SQLite manufacturing analysis |
| `python/` | Data processing, optimization, stress testing, and dashboard generation |
| `notebooks/` | Executed manufacturing analytics notebook |
| `outputs/` | Analytical results, reporting CSVs, and interactive HTML dashboard |
| `powerbi/` | Power BI data model guidance and DAX measures |
| `figures/` | Static dashboard previews |
| `START_HERE_VI.md` | Introductory Vietnamese project guide |
| `PROJECT_REPORT_VI.md` | Detailed business analysis, assumptions, and findings |
| `requirements.txt` | Python dependencies |

### Scenario ID Convention

The scenario IDs `S0`–`S5` generated by the Python optimization framework are separate from the scenario identifiers in the source database's `dim_scenario` table.

The imported `outputs/dim_scenario.csv` corresponds to the Python counterfactual scenario framework.

---

## 11. Data Quality & Model Limitations

### Data Quality

The historical WIP ledger reconciles to the reported WIP snapshot.

However, daily finished-goods snapshot fields appear inconsistent with the reconstructed inventory balance.

Although the snapshot fields remain at zero, opening finished goods plus production minus shipments imply positive inventory at earlier points in the period.

This discrepancy is documented and surfaced in the dashboard rather than concealed.

### Historical Optimization Limitations

The historical optimization uses a deterministic, perfect-hindsight replay.

Real production planners would not know all future demand and operating conditions in advance.

Therefore, the results should be interpreted as estimates of potential improvements under the modeled constraints.

### Forward Planning Limitations

The forward-looking analysis uses simplified demand forecasting and assumed operating conditions.

Forecast accuracy, equipment installation feasibility, labor availability, supplier lead times, and downstream capacity would require validation before implementation.

### Financial Assumptions

Incremental overtime and equipment-related costs are illustrative assumptions.

Reported cost comparisons are intended to demonstrate decision trade-offs rather than verified financial savings.

### Model Validation

A production-ready implementation would require:

- Validated operational data.
- Forecasts available at the decision date.
- Rolling-horizon production planning.
- Realistic labor and maintenance constraints.
- Equipment installation and commissioning lead times.
- Evaluation against held-out actual outcomes.

---

## 12. Final Business Recommendation

**For the historical counterfactual:** Prioritize targeted overtime at Cutting and Grinding as a modeled short-term intervention, subject to cost and operational feasibility.

**For future ramp-up planning:** Evaluate capacity changes across the entire manufacturing line, with particular attention to downstream Polishing constraints after Grinding capacity expansion.

The project demonstrates how manufacturing analytics can support decisions through:

**Data Preparation → Bottleneck Analysis → Capacity Optimization → Stress Testing → Scenario Comparison → Operational Recommendation**

The central finding is that **improving a constrained production stage can increase throughput, but sustainable capacity planning requires managing material flow and anticipating bottleneck migration across the full production process.**

---

**Project Type:** Independent Portfolio Case Study  
**Industry:** Precision Component Manufacturing  
**Data:** 100% Synthetic  
**Year:** 2026  
**Purpose:** Manufacturing Capacity Planning, Supply Management Analytics, and Operational Decision Support

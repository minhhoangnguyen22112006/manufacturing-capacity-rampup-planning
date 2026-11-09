/* 16-week manufacturing analysis — Microsoft SQL Server / SSMS.
   Source objects assumed:
      dbo_clean.fact_production, dbo_clean.dim_machine, dbo_clean.dim_stage,
      dbo_clean.fact_customer_order, stg.fact_shipment, stg.fact_initial_inventory.
   If your shipment/initial inventory tables are in another schema, change stg.
   DO NOT SUM scheduled_minutes across P01/P02 rows: one machine shift is shared.
*/

-- Query 1: throughput, yield, and weekly stage bottlenecks
SELECT TRY_CONVERT(int,p.week_id) AS week_id,
       TRY_CONVERT(int,p.stage_id) AS stage_id,
       s.stage_name,
       SUM(TRY_CONVERT(float,p.input_units)) AS input_units,
       SUM(TRY_CONVERT(float,p.good_units)) AS good_units,
       SUM(TRY_CONVERT(float,p.scrap_units)) AS scrap_units,
       CAST(100.0*SUM(TRY_CONVERT(float,p.good_units))/
            NULLIF(SUM(TRY_CONVERT(float,p.input_units)),0) AS decimal(8,2)) AS yield_pct
FROM dbo_clean.fact_production p
JOIN dbo_clean.dim_stage s ON TRY_CONVERT(int,p.stage_id)=TRY_CONVERT(int,s.stage_id)
WHERE p.record_status='Completed' AND TRY_CONVERT(int,p.week_id) BETWEEN 1 AND 16
GROUP BY TRY_CONVERT(int,p.week_id),TRY_CONVERT(int,p.stage_id),s.stage_name
ORDER BY week_id,stage_id;

-- Query 2: true stage operating minutes (max once per machine/day/shift)
WITH unique_shifts AS (
 SELECT TRY_CONVERT(int,week_id) AS week_id,
        TRY_CONVERT(int,stage_id) AS stage_id,
        machine_id,production_date,shift_id,
        MAX(TRY_CONVERT(float,scheduled_minutes)) AS scheduled_m,
        MAX(TRY_CONVERT(float,planned_downtime_minutes)) AS planned_m,
        MAX(TRY_CONVERT(float,unplanned_downtime_minutes)) AS unplanned_m
 FROM dbo_clean.fact_production
 WHERE record_status='Completed' AND TRY_CONVERT(int,week_id) BETWEEN 1 AND 16
 GROUP BY TRY_CONVERT(int,week_id),TRY_CONVERT(int,stage_id),
          machine_id,production_date,shift_id
)
SELECT week_id,stage_id,COUNT(*) AS machine_shifts,
       SUM(scheduled_m) AS scheduled_minutes,
       SUM(scheduled_m-planned_m-unplanned_m) AS operating_minutes
FROM unique_shifts GROUP BY week_id,stage_id ORDER BY week_id,stage_id;

-- Query 3: WIP flow, assuming zero WIP before week 1 (can adjust for initial inventory)
WITH pg AS (
 SELECT TRY_CONVERT(int,week_id) AS week_id,product_id,
        TRY_CONVERT(int,stage_id) AS stage_id,
        SUM(TRY_CONVERT(float,good_units)) AS good_units,
        SUM(TRY_CONVERT(float,input_units)) AS input_units
 FROM dbo_clean.fact_production
 WHERE record_status='Completed' AND TRY_CONVERT(int,week_id) BETWEEN 1 AND 16
 GROUP BY TRY_CONVERT(int,week_id),product_id,TRY_CONVERT(int,stage_id)
), flow AS (
 SELECT a.week_id,a.product_id,a.stage_id AS after_stage_id,
        a.good_units AS upstream_good,b.input_units AS next_stage_input
 FROM pg a JOIN pg b
   ON b.week_id=a.week_id AND b.product_id=a.product_id
   AND b.stage_id=a.stage_id+1
 WHERE a.stage_id IN (1,2,3)
)
SELECT *, SUM(upstream_good-next_stage_input) OVER (
    PARTITION BY product_id,after_stage_id ORDER BY week_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) AS implied_ending_wip
FROM flow ORDER BY after_stage_id,product_id,week_id;

-- Query 4: shipped vs demand (not equivalent to production vs demand)
WITH order_ship AS (
 SELECT o.order_id,TRY_CONVERT(int,o.week_id) AS week_id,o.product_id,
        TRY_CONVERT(float,o.ordered_units) AS ordered_units,
        COALESCE(SUM(TRY_CONVERT(float,s.shipped_units)),0) AS shipped_units,
        COALESCE(SUM(CASE WHEN TRY_CONVERT(date,s.ship_date)<=TRY_CONVERT(date,o.due_date)
           THEN TRY_CONVERT(float,s.shipped_units) ELSE 0 END),0) AS ontime_shipped_units
 FROM dbo_clean.fact_customer_order o
 LEFT JOIN stg.fact_shipment s ON s.order_id=o.order_id
 WHERE o.order_status='Firm' AND TRY_CONVERT(int,o.week_id) BETWEEN 1 AND 16
 GROUP BY o.order_id,TRY_CONVERT(int,o.week_id),o.product_id,o.ordered_units,o.due_date
)
SELECT week_id,product_id,SUM(ordered_units) AS ordered_units,
       SUM(shipped_units) AS shipped_units,
       SUM(ordered_units-shipped_units) AS unfulfilled_units,
       SUM(ontime_shipped_units) AS ontime_shipped_units
FROM order_ship GROUP BY week_id,product_id ORDER BY week_id,product_id;

-- Query 5: FG inventory ledger. Replace schema for fact_initial_inventory if needed.
WITH finished AS (
 SELECT TRY_CONVERT(int,week_id) AS week_id,product_id,
        SUM(TRY_CONVERT(float,good_units)) AS finished_units
 FROM dbo_clean.fact_production WHERE record_status='Completed'
       AND TRY_CONVERT(int,stage_id)=4 AND TRY_CONVERT(int,week_id) BETWEEN 1 AND 16
 GROUP BY TRY_CONVERT(int,week_id),product_id
),shipped AS (
 SELECT TRY_CONVERT(int,o.week_id) AS week_id,o.product_id,
        SUM(TRY_CONVERT(float,s.shipped_units)) AS shipped_units
 FROM stg.fact_shipment s JOIN dbo_clean.fact_customer_order o ON s.order_id=o.order_id
 GROUP BY TRY_CONVERT(int,o.week_id),o.product_id
)
SELECT f.week_id,f.product_id,
       TRY_CONVERT(float,i.opening_finished_goods_units)
       +SUM(f.finished_units-COALESCE(s.shipped_units,0)) OVER (
         PARTITION BY f.product_id ORDER BY f.week_id
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS calculated_ending_fg
FROM finished f LEFT JOIN shipped s ON f.week_id=s.week_id AND f.product_id=s.product_id
JOIN stg.fact_initial_inventory i ON i.product_id=f.product_id
ORDER BY f.product_id,f.week_id;

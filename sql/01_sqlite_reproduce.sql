-- Source: data/manufacturing_rampup.sqlite (synthetic case)
-- Run via sqlite3 / DB Browser / Python sqlite3. Each query independently executable.
-- Q1. Dataset QA
SELECT 'production_rows' AS metric, COUNT(*) AS value FROM fact_production
UNION ALL SELECT 'completed_production', COUNT(*) FROM fact_production WHERE record_status='Completed'
UNION ALL SELECT 'customer_orders', COUNT(*) FROM fact_customer_order
UNION ALL SELECT 'shipment_events', COUNT(*) FROM fact_shipment
UNION ALL SELECT 'machines',COUNT(*) FROM dim_machine;

-- Q2. Actual throughput and yield by week/stage
SELECT p.week_id, p.stage_id, s.stage_name,
       SUM(p.input_units) AS input_units,
       SUM(p.good_units) AS good_units,
       SUM(p.scrap_units) AS scrap_units,
       ROUND(100.0 * SUM(p.good_units) / NULLIF(SUM(p.input_units),0),2) AS yield_pct
FROM fact_production p JOIN dim_stage s ON s.stage_id=p.stage_id
WHERE p.record_status='Completed'
GROUP BY p.week_id,p.stage_id,s.stage_name
ORDER BY p.week_id,p.stage_id;

-- Q3. Machine-hour dedup (P01/P02 share one shift)
WITH machine_shifts AS (
 SELECT week_id, production_date,shift_id,machine_id,stage_id,
        MAX(scheduled_minutes) AS scheduled_minutes,
        MAX(planned_downtime_minutes) AS planned_dt,
        MAX(unplanned_downtime_minutes) AS unplanned_dt
 FROM fact_production WHERE record_status='Completed'
 GROUP BY week_id,production_date,shift_id,machine_id,stage_id
)
SELECT week_id,stage_id,COUNT(*) AS machine_shifts,
       SUM(scheduled_minutes) AS scheduled_minutes,
       SUM(scheduled_minutes-planned_dt-unplanned_dt) AS operating_minutes
FROM machine_shifts GROUP BY week_id,stage_id
ORDER BY week_id,stage_id;

-- Q4. Physical WIP flow balance (zero initial WIP in fact_initial_inventory)
WITH flow AS (
 SELECT a.week_id,a.product_id,a.stage_id AS after_stage_id,
        SUM(a.good_units) AS upstream_good,
        SUM(b.input_units) AS next_stage_input
 FROM (SELECT week_id,product_id,stage_id,SUM(good_units) AS good_units
       FROM fact_production WHERE record_status='Completed'
       GROUP BY week_id,product_id,stage_id) a
 JOIN (SELECT week_id,product_id,stage_id,SUM(input_units) AS input_units
       FROM fact_production WHERE record_status='Completed'
       GROUP BY week_id,product_id,stage_id) b
  ON a.week_id=b.week_id AND a.product_id=b.product_id AND b.stage_id=a.stage_id+1
 WHERE a.stage_id IN (1,2,3)
 GROUP BY a.week_id,a.product_id,a.stage_id
)
SELECT *, SUM(upstream_good-next_stage_input) OVER (
 PARTITION BY product_id,after_stage_id ORDER BY week_id
 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) AS implied_ending_wip
FROM flow ORDER BY after_stage_id, product_id,week_id;

-- Q5. Actual shipping, orders, on-time shipped units. Unfulfilled != shipped-late.
WITH order_ship AS (
 SELECT o.order_id,o.week_id,o.product_id,o.ordered_units,o.due_date,
        COALESCE(SUM(s.shipped_units),0) AS shipped_units,
        COALESCE(SUM(CASE WHEN s.ship_date<=o.due_date THEN s.shipped_units ELSE 0 END),0) AS ontime_shipped_units
 FROM fact_customer_order o LEFT JOIN fact_shipment s ON o.order_id=s.order_id
 WHERE o.order_status='Firm'
 GROUP BY o.order_id,o.week_id,o.product_id,o.ordered_units,o.due_date
)
SELECT week_id, product_id,SUM(ordered_units) AS demand,
 SUM(shipped_units) AS shipped,
 SUM(ordered_units-shipped_units) AS unfulfilled,
 SUM(ontime_shipped_units) AS ontime_shipped
FROM order_ship GROUP BY week_id,product_id ORDER BY week_id,product_id;

-- Q6. Finished goods flow ledger (not snapshot FG, which is inconsistent in source)
WITH finished AS (
 SELECT week_id,product_id,SUM(good_units) AS finished_units
 FROM fact_production WHERE record_status='Completed' AND stage_id=4
 GROUP BY week_id,product_id
), shipped AS (
 SELECT o.week_id,o.product_id,SUM(s.shipped_units) AS shipped_units
 FROM fact_shipment s JOIN fact_customer_order o ON o.order_id=s.order_id
 GROUP BY o.week_id,o.product_id
)
SELECT f.week_id,f.product_id,
       SUM(f.finished_units - COALESCE(s.shipped_units,0)) OVER (
         PARTITION BY f.product_id ORDER BY f.week_id
       ) + i.opening_finished_goods_units AS calculated_ending_fg
FROM finished f LEFT JOIN shipped s ON f.week_id=s.week_id AND f.product_id=s.product_id
JOIN fact_initial_inventory i ON i.product_id=f.product_id
ORDER BY f.product_id,f.week_id;

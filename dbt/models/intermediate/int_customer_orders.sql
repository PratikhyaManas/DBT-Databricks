-- int_customer_orders.sql
-- Intermediate model: Join customers with their orders
{{ config(
    materialized='view',
    tags=['intermediate']
) }}

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.city,
    c.state,
    o.order_id,
    o.order_date,
    o.total_amount,
    o.status
from {{ ref('stg_customers') }} c
left join {{ ref('stg_orders') }} o
    on c.customer_id = o.customer_id

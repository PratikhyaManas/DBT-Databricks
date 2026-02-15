-- stg_orders.sql
{{ config(
    materialized='view',
    tags=['staging', 'orders']
) }}

select
    order_id,
    customer_id,
    order_date,
    total_amount,
    status,
    created_at,
    updated_at,
    current_timestamp() as dbt_load_timestamp
from {{ source('raw', 'orders') }}
where deleted_at is null

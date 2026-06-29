-- fct_customer_orders.sql
-- Fact table: Customer order facts
{{ config(
    materialized='incremental',
    unique_key='customer_order_key',
    tags=['marts', 'facts']
) }}

with source as (
    select
        customer_id,
        order_id,
        first_name,
        last_name,
        email,
        city,
        state,
        order_date,
        total_amount,
        status
    from {{ ref('int_customer_orders') }}
    where order_id is not null
),

prepared as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id', 'order_id']) }} as customer_order_key,
        customer_id,
        order_id,
        first_name,
        last_name,
        email,
        city,
        state,
        order_date,
        total_amount,
        status,
        current_timestamp() as created_at
    from source
)

select *
from prepared
{% if is_incremental() %}
where order_date >= (
    select coalesce(max(order_date), cast('1900-01-01' as date))
    from {{ this }}
)
{% endif %}

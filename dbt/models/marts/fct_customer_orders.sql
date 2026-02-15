-- fct_customer_orders.sql
-- Fact table: Customer order facts
{{ config(
    materialized='table',
    tags=['marts', 'facts']
) }}

with source as (
    select * from {{ ref('int_customer_orders') }}
),

final as (
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

select * from final

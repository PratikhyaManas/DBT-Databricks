-- dim_customers.sql
-- Dimension table: Customer dimension
{{ config(
    materialized='table',
    tags=['marts', 'dimensions']
) }}

with source as (
    select * from {{ ref('stg_customers') }}
),

final as (
    select
        customer_id,
        first_name,
        last_name,
        email,
        phone,
        address,
        city,
        state,
        zip_code,
        created_at,
        updated_at,
        current_timestamp() as dbt_created_at
    from source
)

select * from final

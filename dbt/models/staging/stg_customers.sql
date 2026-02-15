-- stg_customers.sql
-- Staging layer: Clean and normalize customer data
{{ config(
    materialized='view',
    tags=['staging', 'customers']
) }}

with source_data as (
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
        updated_at
    from {{ source('raw', 'customers') }}
    where deleted_at is null
),

renamed as (
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
        current_timestamp() as dbt_load_timestamp
    from source_data
)

select * from renamed

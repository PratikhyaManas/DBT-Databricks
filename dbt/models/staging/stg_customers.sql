{{ config(
    materialized='view',
    tags=['staging', 'customers']
) }}

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
from {{ source('raw', 'customers') }}
where deleted_at is null

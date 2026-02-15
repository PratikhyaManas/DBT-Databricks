-- tests/test_customer_has_email.sql
-- Test that ensures all customers have valid email addresses

select
    *
from {{ ref('dim_customers') }}
where email is null or email = ''

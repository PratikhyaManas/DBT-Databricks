-- macros/get_date_spine.sql
-- Generate a spine of dates for joining

{% macro generate_date_spine(start_date, end_date) %}

with spine as (
    select 
        sequence(
            to_date('{{ start_date }}'),
            to_date('{{ end_date }}'),
            interval 1 day
        ) as dates
    )
    
select 
    dates as date_day
from spine
lateral view explode(dates)

{% endmacro %}

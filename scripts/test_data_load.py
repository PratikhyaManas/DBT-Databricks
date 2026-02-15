#!/usr/bin/env python3
"""
Load sample test data to Databricks for dbt testing
"""

import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.data_types import StructType, StructField, StringType, LongType
import pandas as pd


def create_sample_customers(ws: WorkspaceClient, catalog: str, schema: str):
    """Create sample customers table"""
    data = {
        'customer_id': [1, 2, 3, 4, 5],
        'first_name': ['John', 'Jane', 'Bob', 'Alice', 'Charlie'],
        'last_name': ['Doe', 'Smith', 'Johnson', 'Williams', 'Brown'],
        'email': ['john@example.com', 'jane@example.com', 'bob@example.com', 
                  'alice@example.com', 'charlie@example.com'],
        'phone': ['555-0001', '555-0002', '555-0003', '555-0004', '555-0005'],
        'address': ['123 Main St', '456 Oak Ave', '789 Elm St', '321 Pine Rd', '654 Maple Dr'],
        'city': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
        'state': ['NY', 'CA', 'IL', 'TX', 'AZ'],
        'zip_code': ['10001', '90001', '60601', '77001', '85001'],
        'created_at': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'],
        'updated_at': ['2024-01-15', '2024-01-15', '2024-01-15', '2024-01-15', '2024-01-15'],
        'deleted_at': [None, None, None, None, None]
    }
    
    df = pd.DataFrame(data)
    
    # Write to Databricks
    table_path = f"{catalog}.{schema}.customers"
    spark_df = ws.tables.get(table_path)
    df.to_spark().write.mode("overwrite").option("mergeSchema", "true").saveAsTable(table_path)
    
    print(f"✅ Created sample customers table: {table_path}")


def create_sample_orders(ws: WorkspaceClient, catalog: str, schema: str):
    """Create sample orders table"""
    data = {
        'order_id': [101, 102, 103, 104, 105, 106],
        'customer_id': [1, 2, 1, 3, 2, 4],
        'order_date': ['2024-01-10', '2024-01-11', '2024-01-12', '2024-01-13', '2024-01-14', '2024-01-15'],
        'total_amount': [150.00, 200.50, 75.25, 300.00, 125.75, 450.00],
        'status': ['completed', 'completed', 'pending', 'completed', 'shipped', 'completed'],
        'created_at': ['2024-01-10', '2024-01-11', '2024-01-12', '2024-01-13', '2024-01-14', '2024-01-15'],
        'updated_at': ['2024-01-15', '2024-01-15', '2024-01-15', '2024-01-15', '2024-01-15', '2024-01-15'],
        'deleted_at': [None, None, None, None, None, None]
    }
    
    df = pd.DataFrame(data)
    
    # Write to Databricks
    table_path = f"{catalog}.{schema}.orders"
    df.to_spark().write.mode("overwrite").option("mergeSchema", "true").saveAsTable(table_path)
    
    print(f"✅ Created sample orders table: {table_path}")


def main():
    # Initialize Databricks client
    ws = WorkspaceClient(
        host=os.getenv("DATABRICKS_HOST"),
        token=os.getenv("DATABRICKS_TOKEN")
    )
    
    catalog = os.getenv("CATALOG", "hive_metastore")
    schema = os.getenv("DATA_SCHEMA", "raw")
    
    print(f"\nLoading test data to {catalog}.{schema}...")
    
    # Create schema if not exists
    try:
        ws.schemas.get(f"{catalog}.{schema}")
    except Exception:
        ws.schemas.create(name=schema, catalog_name=catalog)
        print(f"✅ Created schema: {catalog}.{schema}")
    
    # Create sample tables
    create_sample_customers(ws, catalog, schema)
    create_sample_orders(ws, catalog, schema)
    
    print("\n✅ Test data loaded successfully!")


if __name__ == "__main__":
    main()

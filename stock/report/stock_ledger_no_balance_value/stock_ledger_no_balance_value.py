import frappe
from erpnext.stock.report.stock_ledger.stock_ledger import execute as original_execute

def execute(filters=None):
    columns, data = original_execute(filters)
    
    # Filter out unwanted columns
    unwanted_labels = {
        "Incoming Rate", 
        "Valuation Rate", 
        "Balance Value", 
        "Value Difference", 
        "Avg Rate"
    }

    # Find indexes of unwanted columns
    unwanted_indexes = [
        i for i, col in enumerate(columns)
        if col.get("label") in unwanted_labels
    ]

    # Filter columns
    filtered_columns = [
        col for i, col in enumerate(columns) if i not in unwanted_indexes
    ]

    # Filter data rows
    filtered_data = [
        [val for i, val in enumerate(row) if i not in unwanted_indexes]
        for row in data
    ]

    return filtered_columns, filtered_data

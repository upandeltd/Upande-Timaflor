# Copyright (c) 2025, newton@upande.com and contributors
import frappe  # <-- ADD THIS AT THE TOP
from frappe.model.document import Document
from datetime import datetime

class OrderingSheet(Document):
    pass
@frappe.whitelist()
def get_average_consumption(item_code, from_date, to_date):
    """Calculate average daily consumption of an item per FARM (not warehouse)"""
    from_date = datetime.strptime(from_date, "%Y-%m-%d")
    to_date = datetime.strptime(to_date, "%Y-%m-%d")

    days = (to_date - from_date).days
    if days <= 0:
        return {}

    # Group consumption by FARM (not warehouse)
    stock_movement = frappe.db.sql("""
        SELECT 
            w.farm AS farm,
            SUM(sle.actual_qty) AS total_qty
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        WHERE 
            sle.item_code = %s 
            AND sle.posting_date BETWEEN %s AND %s
            AND w.farm IS NOT NULL  # Exclude warehouses not linked to a farm
        GROUP BY w.farm
    """, (item_code, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")), as_dict=True)

    averages = {}
    for entry in stock_movement:
        farm = entry.farm
        total_qty = entry.total_qty or 0
        avg = total_qty / days if days else 0
        averages[farm] = avg

    return averages
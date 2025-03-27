# Copyright (c) 2025, newton@upande.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime

class OrderingSheet(Document):
    pass  # Keep this class if you need to customize other behavior

@frappe.whitelist()
def get_average_consumption(item_code, from_date, to_date):
    """Calculate average daily consumption of an item"""
    from_date = datetime.strptime(from_date, "%Y-%m-%d")
    to_date = datetime.strptime(to_date, "%Y-%m-%d")

    days = (to_date - from_date).days
    if days <= 0:
        return 0  # Avoid division by zero

    stock_movement = frappe.db.sql("""
        SELECT SUM(actual_qty) as total_qty 
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s AND posting_date BETWEEN %s AND %s
    """, (item_code, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")), as_dict=True)

    total_qty = stock_movement[0].total_qty if stock_movement and stock_movement[0].total_qty else 0
    return total_qty / days if total_qty else 0

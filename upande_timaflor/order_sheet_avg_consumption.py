import frappe
from datetime import datetime

@frappe.whitelist()  # Allows calling from JavaScript
def get_average_consumption(item_code, from_date, to_date):
    from_date = datetime.strptime(from_date, "%Y-%m-%d")
    to_date = datetime.strptime(to_date, "%Y-%m-%d")

    days = (to_date - from_date).days
    print(f"Calculated days: {days}")  # Debugging step

    if days <= 0:
        return 0  # Avoid division by zero

    stock_movement = frappe.db.sql("""
        SELECT SUM(actual_qty) as total_qty 
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s AND posting_date BETWEEN %s AND %s
    """, (item_code, from_date, to_date), as_dict=True)

    total_qty = stock_movement[0].total_qty if stock_movement and stock_movement[0].total_qty else 0
    print(f"Total Qty: {total_qty}")  # Debugging step

    return total_qty / days if total_qty else 0

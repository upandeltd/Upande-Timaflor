# Copyright (c) 2025, newton@upande.com and contributors
import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe import _
import json

class OrderingSheet(Document):
    @frappe.whitelist()
    def create_purchase_order(self, supplier=None):
        """Create Purchase Order from Ordering Sheet"""
        # Validate required fields
        if not self.order_quantity:
            frappe.throw(_("No order quantities available - please calculate order quantities first"))

        # Determine final supplier
        final_supplier = supplier or self.supplier
        if not final_supplier:
            frappe.throw(_("Supplier must be selected during PO creation"))

        # Create new Purchase Order
        po = frappe.new_doc("Purchase Order")
        po.supplier = final_supplier
        po.company = frappe.defaults.get_user_default("Company")
        
        # Add items from order quantity table
        for order_item in self.order_quantity:
            total_qty = sum([
                order_item.tima_1 or 0,
                order_item.tima_2 or 0,
                order_item.tima_3 or 0,
                order_item.tima_4 or 0,
                order_item.tima_5 or 0,
                order_item.tima_6 or 0,
                order_item.tima_7 or 0,
                order_item.jangwani or 0  # Added Jangwani to total calculation
            ])

            if total_qty > 0:
                po.append("items", {
                    "item_code": order_item.item,
                    "qty": total_qty,
                    "schedule_date": frappe.utils.nowdate()
                })

        if not po.get("items"):
            frappe.throw(_("No items with positive quantities found"))

        po.insert(ignore_permissions=True)
        po.submit()
        frappe.db.commit()
        return po.name

@frappe.whitelist()
def get_average_consumption(item_code, from_date, to_date):
    """Calculate average daily consumption of an item per FARM"""
    from_date = datetime.strptime(from_date, "%Y-%m-%d")
    to_date = datetime.strptime(to_date, "%Y-%m-%d")

    days = (to_date - from_date).days
    if days <= 0: return {}

    stock_movement = frappe.db.sql("""
        SELECT 
            w.farm AS farm,
            SUM(sle.actual_qty) AS total_qty
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        WHERE 
            sle.item_code = %s 
            AND sle.posting_date BETWEEN %s AND %s
            AND w.farm IS NOT NULL
        GROUP BY w.farm
    """, (item_code, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")), as_dict=True)

    return {entry.farm: (entry.total_qty or 0)/days for entry in stock_movement if days}

@frappe.whitelist()
def get_all_consumption_data(item_codes, from_date, to_date):
    """
    Fetch average, minimum, and maximum consumption data for given items and date range
    
    Args:
        item_codes (list): List of item codes
        from_date (str): Start date for consumption data
        to_date (str): End date for consumption data
        
    Returns:
        dict: Dictionary with average, minimum, and maximum consumption data
    """
    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)
    
    # Convert dates to datetime objects
    from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
    to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
    days = (to_date_obj - from_date_obj).days
    
    if days <= 0: 
        return {
            "average": {},
            "minimum": {},
            "maximum": {}
        }
    
    result = {
        "average": {},
        "minimum": {},
        "maximum": {}
    }
    
    # Process each item
    for item_code in item_codes:
        # Initialize data structures for this item
        result["average"][item_code] = {}
        result["minimum"][item_code] = {}
        result["maximum"][item_code] = {}
        
        # Get data for all farms by querying stock ledger entries
        stock_data = frappe.db.sql("""
            SELECT 
                w.farm AS farm,
                DATE(sle.posting_date) AS posting_date,
                SUM(sle.actual_qty) AS daily_qty
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
            WHERE 
                sle.item_code = %s 
                AND sle.posting_date BETWEEN %s AND %s
                AND w.farm IS NOT NULL
            GROUP BY w.farm, DATE(sle.posting_date)
        """, (item_code, from_date, to_date), as_dict=True)
        
        # Process the data by farm
        farm_daily_data = {}
        for entry in stock_data:
            farm = entry.farm
            if farm not in farm_daily_data:
                farm_daily_data[farm] = []
            
            farm_daily_data[farm].append(entry.daily_qty)
        
        # Calculate statistics for each farm
        for farm, daily_values in farm_daily_data.items():
            if daily_values:
                # Calculate average
                avg_consumption = sum(daily_values) / len(daily_values)
                result["average"][item_code][farm] = avg_consumption
                
                # Calculate minimum
                min_consumption = min(daily_values)
                result["minimum"][item_code][farm] = min_consumption
                
                # Calculate maximum
                max_consumption = max(daily_values)
                result["maximum"][item_code][farm] = max_consumption
            else:
                # No data for this farm
                result["average"][item_code][farm] = 0
                result["minimum"][item_code][farm] = 0
                result["maximum"][item_code][farm] = 0
        
        # Handle farms with no data
        all_farms = ["Tima1", "Tima2", "Tima3", "Tima4", "Tima5", "Tima6", "Tima7", "Jangwani"]
        for farm in all_farms:
            if farm not in farm_daily_data:
                result["average"][item_code][farm] = 0
                result["minimum"][item_code][farm] = 0
                result["maximum"][item_code][farm] = 0
    
    return result
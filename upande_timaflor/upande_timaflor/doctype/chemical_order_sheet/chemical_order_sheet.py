# Copyright (c) 2025, newton@upande.com
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from frappe.utils import flt

class ChemicalOrderSheet(Document):
    def validate(self):
        pass

@frappe.whitelist()
def get_stock_for_all_chemicals():
    """Get stock quantities for all chemicals at once"""
    try:
        stock_data = {}
        chemicals = frappe.get_all("Item", 
            filters={"item_group": "Chemical", "disabled": 0},
            fields=["name"]
        )
        
        for chem in chemicals:
            stock_data[chem["name"]] = get_item_stock(chem["name"])
            
        return stock_data
    except Exception as e:
        frappe.log_error(f"Stock fetch error: {str(e)}")
        return {}

@frappe.whitelist()
def get_all_chemicals_with_details():
    """Get chemicals with guaranteed field names"""
    try:
        fields = ["name", "item_name"]
        custom_fields = {
            "application_rate": "custom_application_rate_per_ha",
            "required_sprays": "custom_advised_no_sprays",
            "number_of_sprays": "custom_no_of_sprays"
        }
        
        # Add existing custom fields
        meta = frappe.get_meta("Item")
        for field, df in custom_fields.items():
            if meta.has_field(df):
                fields.append(f"`{df}` as {field}")
        
        chemicals = frappe.get_all("Item",
            filters={"item_group": "Chemical", "disabled": 0},
            fields=fields
        )
        
        # Fallback for missing custom fields
        for chem in chemicals:
            chem.setdefault("application_rate", 0)
            chem.setdefault("required_sprays", 0)
            chem.setdefault("number_of_sprays", 0)
        
        return chemicals
    except Exception as e:
        frappe.log_error(f"Chemical fetch error: {str(e)}")
        return []

@frappe.whitelist()
def get_chemical_details(item_code):
    """Get details for a single chemical"""
    try:
        fields = ["item_name"]
        custom_fields = {
            "application_rate": "custom_application_rate_per_ha",
            "required_sprays": "custom_advised_no_sprays",
            "number_of_sprays": "custom_no_of_sprays"
        }
        
        # Add existing custom fields
        meta = frappe.get_meta("Item")
        for field, df in custom_fields.items():
            if meta.has_field(df):
                fields.append(f"`{df}` as {field}")
        
        chem = frappe.db.get_value("Item", item_code, fields, as_dict=True)
        
        # Fallback for missing custom fields
        if chem:
            chem.setdefault("application_rate", 0)
            chem.setdefault("required_sprays", 0)
            chem.setdefault("number_of_sprays", 0)
            return chem
            
        return {}
    except Exception as e:
        frappe.log_error(f"Chemical details error: {str(e)}")
        return {}

@frappe.whitelist()
def calculate_order_quantities(doc, stock_data=None):
    """Calculate with correct formula and stock deduction"""
    try:
        doc = json.loads(doc) if isinstance(doc, str) else doc
        stock_data = json.loads(stock_data) if isinstance(stock_data, str) else stock_data or {}
        
        if not doc.get("farm_area_to_spray") or not doc.get("spray_details"):
            return []

        # 1. Calculate total area per greenhouse
        area_totals = {
            "tima_1": 0, "tima_2": 0, "tima_3": 0, "tima_4": 0,
            "tima_5": 0, "tima_6": 0, "tima_7": 0, "jangwani": 0
        }
        
        for area in doc.get("farm_area_to_spray", []):
            for field in area_totals.keys():
                area_totals[field] += flt(area.get(field, 0))

        # 2. Calculate required quantity per chemical
        order_details = []
        for spray in doc.get("spray_details", []):
            if not spray.get("chemical"):
                continue
                
            item_code = spray["chemical"]
            item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
            
            # Get parameters with defaults
            app_rate = flt(spray.get("application_rate_per_hectare", 0))
            num_sprays = flt(spray.get("number_of_sprays", 0))
            current_stock = flt(stock_data.get(item_code, 0))
            
            # Calculate total required
            required_total = 0
            order_row = {"item": item_code, "item_name": item_name}
            
            # Initialize all greenhouse fields to 0
            for field in area_totals.keys():
                order_row[field] = 0
            
            # Calculate requirements per greenhouse
            for field, area in area_totals.items():
                field_required = area * app_rate * num_sprays
                required_total += field_required
                order_row[field] = field_required
            
            # 3. Deduct stock from total
            if current_stock > 0 and required_total > 0:
                if current_stock >= required_total:
                    # Enough stock - no order needed
                    for field in area_totals.keys():
                        order_row[field] = 0
                else:
                    # Partial stock - deduct proportionally
                    deduction_ratio = (required_total - current_stock) / required_total
                    for field in area_totals.keys():
                        order_row[field] = flt(order_row[field] * deduction_ratio, 2)
            
            order_details.append(order_row)
            
        return order_details
        
    except Exception as e:
        frappe.log_error(f"Calculation error: {str(e)}")
        return []

@frappe.whitelist()
def get_item_stock(item_code):
    """Get current stock quantity for an item"""
    try:
        if not frappe.db.exists("Item", item_code):
            return 0

        stock_qty = frappe.db.sql("""
            SELECT SUM(actual_qty) as qty
            FROM `tabBin`
            WHERE item_code = %s
        """, (item_code,), as_dict=1)  

        return flt(stock_qty[0].qty) if stock_qty and stock_qty[0].qty else 0
    except Exception as e:
        frappe.log_error(f"Stock error: {item_code}", "Stock Error")
        return 0
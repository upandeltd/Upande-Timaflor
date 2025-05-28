# Copyright (c) 2025, newton@upande.com
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

class ChemicalOrderSheet(Document):
    def validate(self):
        # Skip auto-calculation on validation
        pass
    
    def calculate_order_quantities_internal(self):
        """Calculate order quantities based on farm areas, application rate, and spray count"""
        if not self.farm_area_to_spray or not self.spray_details:
            return

        self.order_detail = []

        for spray in self.spray_details:
            if not spray.chemical or not spray.application_rate_per_hectare or not spray.number_of_sprays:
                continue
            
            item_code = spray.chemical
            if not frappe.db.exists("Item", item_code):
                frappe.log_error(f"Item {item_code} not found", "ChemicalOrderSheet")
                continue

            item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code

            order_row = {
                "item": item_code,
                "item_name": item_name,
                "tima_1": 0, "tima_2": 0, "tima_3": 0, "tima_4": 0,
                "tima_5": 0, "tima_6": 0, "tima_7": 0, "jangwani": 0
            }

            for area in self.farm_area_to_spray:
                for field in order_row.keys():
                    if field in ["item", "item_name"]:
                        continue
                    try:
                        area_size = float(getattr(area, field) or 0)
                        app_rate = float(spray.application_rate_per_hectare or 0)
                        spray_count = float(spray.number_of_sprays or 0)
                        order_row[field] += area_size * app_rate * spray_count
                    except Exception as e:
                        frappe.log_error(f"Error calculating {field} for {item_code}: {str(e)}", "ChemicalOrderSheet")

            current_stock = get_item_stock(item_code)
            for field in order_row.keys():
                if field in ["item", "item_name"]:
                    continue
                if order_row[field] > 0:
                    if current_stock >= order_row[field]:
                        current_stock -= order_row[field]
                        order_row[field] = 0
                    else:
                        order_row[field] -= current_stock
                        current_stock = 0
                if current_stock <= 0:
                    break

            self.append("order_detail", order_row)

        self.calculate_total_amount()

    def calculate_total_amount(self):
        total = 0
        try:
            if not any(field.fieldname == 'total_order_amount'
                       for field in frappe.get_meta(self.doctype).fields):
                frappe.log_error(f"'total_order_amount' field missing in {self.doctype}", "ChemicalOrderSheet")
                return
        except Exception as e:
            frappe.log_error(f"Meta error: {str(e)}", "ChemicalOrderSheet")
            return

        for item in self.order_detail:
            try:
                item_code = item.item
                total_qty = sum(float(getattr(item, field) or 0)
                                for field in ["tima_1", "tima_2", "tima_3", "tima_4",
                                              "tima_5", "tima_6", "tima_7", "jangwani"])
                rate = frappe.db.get_value("Item", item_code, "valuation_rate") or 0
                total += total_qty * float(rate)
            except Exception as e:
                frappe.log_error(f"Error calculating total for {item_code}: {str(e)}", "ChemicalOrderSheet")

        self.total_order_amount = total


@frappe.whitelist()
def get_all_chemicals():
    """Get all chemicals from Item master - DEBUG VERSION"""
    try:
        # Log method entry
        frappe.log_error("get_all_chemicals method called", "ChemicalOrderSheet Debug")
        
        # First, let's check if Chemical item group exists
        if not frappe.db.exists("Item Group", "Chemical"):
            frappe.log_error("Chemical Item Group does not exist", "ChemicalOrderSheet Debug")
            return []
        
        # Get basic chemical data first (without custom fields to avoid errors)
        chemicals = frappe.get_all("Item", 
            filters={
                "item_group": "Chemical",
                "disabled": 0  # Only get enabled items
            },  
            fields=["name", "item_name"]
        )
        
        # Log results
        frappe.log_error(f"get_all_chemicals: Found {len(chemicals)} enabled chemicals", "ChemicalOrderSheet Debug")
        
        # Log first few chemicals for debugging
        if chemicals:
            sample_chemicals = chemicals[:5]  # First 5 chemicals
            frappe.log_error(f"Sample chemicals: {sample_chemicals}", "ChemicalOrderSheet Debug")
        
        return chemicals
        
    except Exception as e:
        error_msg = f"Error in get_all_chemicals: {str(e)}"
        frappe.log_error(error_msg, "ChemicalOrderSheet Debug")
        # Also log to console if running in development
        print(error_msg)
        return []


@frappe.whitelist()
def get_all_chemicals_with_custom_fields():
    """Get all chemicals with custom fields - separate method for testing"""
    try:
        frappe.log_error("get_all_chemicals_with_custom_fields called", "ChemicalOrderSheet Debug")
        
        # Check which custom fields exist
        meta = frappe.get_meta("Item")
        available_fields = ["name", "item_name"]
        
        custom_fields = [
            "custom_application_rate_per_ha", 
            "custom_advised_no_sprays", 
            "custom_no_of_sprays"
        ]
        
        existing_custom_fields = []
        for field in custom_fields:
            if meta.has_field(field):
                available_fields.append(field)
                existing_custom_fields.append(field)
        
        frappe.log_error(f"Available custom fields: {existing_custom_fields}", "ChemicalOrderSheet Debug")
        
        chemicals = frappe.get_all("Item", 
            filters={
                "item_group": "Chemical",
                "disabled": 0
            },  
            fields=available_fields
        )
        
        frappe.log_error(f"Found {len(chemicals)} chemicals with custom fields", "ChemicalOrderSheet Debug")
        return chemicals
        
    except Exception as e:
        error_msg = f"Error in get_all_chemicals_with_custom_fields: {str(e)}"
        frappe.log_error(error_msg, "ChemicalOrderSheet Debug")
        return []


@frappe.whitelist()
def debug_chemical_count():
    """Debug helper to check chemical counts"""
    try:
        # Count all items
        total_items = frappe.db.count("Item")
        
        # Count chemical items
        chemical_items = frappe.db.count("Item", {"item_group": "Chemical"})
        
        # Count enabled chemical items
        enabled_chemical_items = frappe.db.count("Item", {
            "item_group": "Chemical", 
            "disabled": 0
        })
        
        # Check if Chemical item group exists
        chemical_group_exists = frappe.db.exists("Item Group", "Chemical")
        
        result = {
            "total_items": total_items,
            "chemical_items": chemical_items,
            "enabled_chemical_items": enabled_chemical_items,
            "chemical_group_exists": chemical_group_exists
        }
        
        frappe.log_error(f"Debug counts: {result}", "ChemicalOrderSheet Debug")
        return result
        
    except Exception as e:
        error_msg = f"Error in debug_chemical_count: {str(e)}"
        frappe.log_error(error_msg, "ChemicalOrderSheet Debug")
        return {"error": error_msg}


@frappe.whitelist()
def get_item_stock(item_code):
    try:
        if not frappe.db.exists("Item", item_code):
            return 0

        stock_qty = frappe.db.sql("""
            SELECT SUM(actual_qty) as qty
            FROM `tabBin`
            WHERE item_code = %s
        """, (item_code,), as_dict=1)  

        return float(stock_qty[0].qty) if stock_qty and stock_qty[0].qty else 0
    except Exception as e:
        frappe.log_error(f"Error fetching stock for {item_code}: {str(e)}", "ChemicalOrderSheet")
        return 0


@frappe.whitelist()
def calculate_order_quantities(doc):
    try:
        if isinstance(doc, str):
            doc = json.loads(doc)

        if not doc.get('farm_area_to_spray') or not doc.get('spray_details'):
            return []

        order_details = []

        for spray in doc.get('spray_details'):
            if not spray.get('chemical') or not spray.get('application_rate_per_hectare') or not spray.get('number_of_sprays'):
                continue

            item_code = spray.get('chemical')
            if not frappe.db.exists("Item", item_code):
                continue

            item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code

            order_row = {
                "item": item_code,
                "item_name": item_name,
                "tima_1": 0, "tima_2": 0, "tima_3": 0, "tima_4": 0,
                "tima_5": 0, "tima_6": 0, "tima_7": 0, "jangwani": 0
            }

            for area in doc.get('farm_area_to_spray'):
                for field in order_row.keys():
                    if field in ["item", "item_name"]:
                        continue
                    try:
                        area_size = float(area.get(field) or 0)
                        app_rate = float(spray.get('application_rate_per_hectare') or 0)
                        spray_count = float(spray.get('number_of_sprays') or 0)
                        order_row[field] += area_size * app_rate * spray_count
                    except Exception as e:
                        frappe.log_error(f"Calc error {field} for {item_code}: {str(e)}", "ChemicalOrderSheet")

            current_stock = get_item_stock(item_code)
            for field in order_row.keys():
                if field in ["item", "item_name"]:
                    continue
                if order_row[field] > 0:
                    if current_stock >= order_row[field]:
                        current_stock -= order_row[field]
                        order_row[field] = 0
                    else:
                        order_row[field] -= current_stock
                        current_stock = 0
                if current_stock <= 0:
                    break

            order_details.append(order_row)

        return order_details

    except Exception as e:
        frappe.log_error(f"Error in calc_order_quantities: {str(e)}", "ChemicalOrderSheet")
        return []
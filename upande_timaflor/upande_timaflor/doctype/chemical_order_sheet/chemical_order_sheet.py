# Copyright (c) 2025, newton@upande.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

class ChemicalOrderSheet(Document):
    def validate(self):
        self.calculate_order_quantities_internal()
    
    def calculate_order_quantities_internal(self):
        """Calculate order quantities based on farm areas, application rate, and spray count"""
        if not self.farm_area_to_spray or not self.spray_details:
            return
        
        # Clear existing order details
        self.order_detail = []
        
        # Process each chemical from spray details
        for spray in self.spray_details:
            if not spray.chemical or not spray.application_rate_per_hectare or not spray.number_of_sprays:
                continue
            
            try:
                # Get item details
                item = frappe.get_doc("Item", spray.chemical)
                
                # Create new order detail row
                order_row = {
                    "item": spray.chemical,
                    "item_name": item.item_name,
                    "tima_1": 0,
                    "tima_2": 0,
                    "tima_3": 0,
                    "tima_4": 0,
                    "tima_5": 0,
                    "tima_6": 0,
                    "tima_7": 0,
                    "jangwani": 0
                }
                
                # Calculate for each farm area
                for area in self.farm_area_to_spray:
                    # Calculate required quantity for each area
                    # Formula: Area size * Application Rate * Number of Sprays
                    if area.tima_1:
                        order_row["tima_1"] = float(area.tima_1) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                    if area.tima_2:
                        order_row["tima_2"] = float(area.tima_2) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                    if area.tima_3:
                        order_row["tima_3"] = float(area.tima_3) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                    if area.tima_4:
                        order_row["tima_4"] = float(area.tima_4) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                    if area.tima_5:
                        order_row["tima_5"] = float(area.tima_5) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                    if area.tima_6:
                        order_row["tima_6"] = float(area.tima_6) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                    if area.tima_7:
                        order_row["tima_7"] = float(area.tima_7) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                    if area.jangwani:
                        order_row["jangwani"] = float(area.jangwani) * float(spray.application_rate_per_hectare) * float(spray.number_of_sprays)
                
                # Get current stock (safely handle possible None return)
                current_stock = get_item_stock(spray.chemical) or 0
                
                # Subtract current stock from the first non-zero area (priority order)
                if current_stock > 0:
                    for field in ["tima_1", "tima_2", "tima_3", "tima_4", "tima_5", "tima_6", "tima_7", "jangwani"]:
                        if order_row[field] > 0:
                            if current_stock >= order_row[field]:
                                current_stock -= order_row[field]
                                order_row[field] = 0
                            else:
                                order_row[field] -= current_stock
                                current_stock = 0
                        
                        if current_stock <= 0:
                            break
                
                # Add to parent document
                self.append("order_detail", order_row)
            
            except Exception as e:
                frappe.log_error(f"Error processing chemical {spray.chemical}: {str(e)}", "ChemicalOrderSheet")
                continue
        
        # Calculate total order amount
        self.calculate_total_amount()
    
    def calculate_total_amount(self):
        """Calculate total order amount"""
        total = 0
        
        # Check if total_order_amount field exists in the doctype
        field_exists = False
        try:
            # Try to get the field metadata
            doctype_fields = frappe.get_meta(self.doctype).fields
            field_exists = any(field.fieldname == 'total_order_amount' for field in doctype_fields)
            
            if not field_exists:
                frappe.log_error(
                    f"Field 'total_order_amount' not found in DocType '{self.doctype}'. "
                    f"Please add this field via Customize Form.",
                    "ChemicalOrderSheet"
                )
        except Exception as e:
            frappe.log_error(f"Error checking for total_order_amount field: {str(e)}", "ChemicalOrderSheet")
        
        for item in self.order_detail:
            try:
                # Calculate total quantity for this item
                total_qty = (
                    (float(item.tima_1 or 0)) + 
                    (float(item.tima_2 or 0)) + 
                    (float(item.tima_3 or 0)) + 
                    (float(item.tima_4 or 0)) + 
                    (float(item.tima_5 or 0)) + 
                    (float(item.tima_6 or 0)) + 
                    (float(item.tima_7 or 0)) + 
                    (float(item.jangwani or 0))
                )
                
                # Get item rate (safely handle possible None return)
                rate = frappe.get_value("Item", item.item, "valuation_rate") or 0
                
                # Add to total
                total += total_qty * rate
            
            except Exception as e:
                frappe.log_error(f"Error calculating total for item {item.item}: {str(e)}", "ChemicalOrderSheet")
                continue
        
        # Always set the total_order_amount, even if the field doesn't exist
        # The document will still save but the field won't be displayed
        try:
            self.total_order_amount = total
        except Exception as e:
            frappe.log_error(f"Error setting total_order_amount: {str(e)}", "ChemicalOrderSheet")

@frappe.whitelist()
def get_all_chemicals():
    """Get all chemical items with their application rates"""
    try:
        chemicals = frappe.get_all('Item', 
            filters={'item_group': 'Chemical', 'disabled': 0},
            fields=['name', 'item_name']
        )
        
        # Log success for debugging
        frappe.logger().debug(f"Retrieved {len(chemicals)} chemicals")
        
        return chemicals
    
    except Exception as e:
        frappe.log_error(f"Error fetching chemicals: {str(e)}", "ChemicalOrderSheet")
        return []

@frappe.whitelist()
def get_item_stock(item_code):
    """Get current stock of an item across all warehouses"""
    try:
        stock_qty = frappe.db.sql("""
            SELECT SUM(actual_qty) as qty
            FROM `tabBin`
            WHERE item_code = %s
        """, (item_code), as_dict=1)
        
        return float(stock_qty[0].qty) if stock_qty and stock_qty[0].qty else 0
    
    except Exception as e:
        frappe.log_error(f"Error fetching stock for item {item_code}: {str(e)}", "ChemicalOrderSheet")
        return 0

@frappe.whitelist()
def calculate_order_quantities(doc):
    """Calculate order quantities based on farm areas, application rate, and spray count"""
    try:
        if isinstance(doc, str):
            doc = json.loads(doc)
        
        if not doc.get('farm_area_to_spray') or not doc.get('spray_details'):
            return []
        
        order_details = []
        
        # Process each chemical from spray details
        for spray in doc.get('spray_details'):
            if not spray.get('chemical') or not spray.get('application_rate_per_hectare') or not spray.get('number_of_sprays'):
                continue
            
            # Get item details
            item_name = frappe.get_value("Item", spray.get('chemical'), "item_name")
            if not item_name:
                frappe.logger().warning(f"Item {spray.get('chemical')} not found")
                continue
                
            # Create new order detail row
            order_row = {
                "item": spray.get('chemical'),
                "item_name": item_name,
                "tima_1": 0,
                "tima_2": 0,
                "tima_3": 0,
                "tima_4": 0,
                "tima_5": 0,
                "tima_6": 0,
                "tima_7": 0,
                "jangwani": 0
            }
            
            # Calculate for each farm area
            for area in doc.get('farm_area_to_spray'):
                # Calculate required quantity for each area
                # Formula: Area size * Application Rate * Number of Sprays
                for field in ["tima_1", "tima_2", "tima_3", "tima_4", "tima_5", "tima_6", "tima_7", "jangwani"]:
                    if area.get(field):
                        try:
                            # Ensure all values are properly converted to float
                            area_size = float(area.get(field) or 0)
                            app_rate = float(spray.get('application_rate_per_hectare') or 0)
                            spray_count = float(spray.get('number_of_sprays') or 0)
                            
                            order_row[field] = area_size * app_rate * spray_count
                        except (ValueError, TypeError) as e:
                            frappe.logger().warning(f"Error calculating {field}: {str(e)}")
                            order_row[field] = 0
            
            # Get current stock
            current_stock = get_item_stock(spray.get('chemical'))
            
            # Subtract current stock from the first non-zero area (priority order)
            if current_stock > 0:
                for field in ["tima_1", "tima_2", "tima_3", "tima_4", "tima_5", "tima_6", "tima_7", "jangwani"]:
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
        frappe.log_error(f"Error calculating order quantities: {str(e)}", "ChemicalOrderSheet")
        return []
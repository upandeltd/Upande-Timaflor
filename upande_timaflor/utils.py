import frappe
from frappe import _
from frappe.utils import flt

def validate_bom(doc, method):
    """BOM Validation Logic for Timaflor custom fields"""
    for item in doc.items:
        if not item.item_code:
            continue

        rate_type = item.get("custom_application_rate_type")
        
        if rate_type == "Per Hectare":
            validate_per_hectare(item)
        elif rate_type == "Per 100L":
            validate_per_100l(item)

def validate_per_hectare(item):
    """Validate Per Hectare application rate requirements"""
    if not item.get("custom_application_rate_per_ha"):
        frappe.throw(_(f"Row {item.idx}: Application Rate (per ha) required for {item.item_code}"))
    
    if flt(item.custom_application_rate_per_ha) <= 0:
        frappe.throw(_(f"Row {item.idx}: Application Rate must be > 0 for {item.item_code}"))
    
    if not item.get("custom_area_to_spray"):
        frappe.throw(_(f"Row {item.idx}: Area to Spray required for {item.item_code}"))
    
    if item.get("custom_volume"):
        frappe.throw(_(f"Row {item.idx}: Remove Water Volume for Per Hectare items"))

def validate_per_100l(item):
    """Validate Per 100L application volume requirements"""
    if not item.get("custom_application_volume_per_10002000l"):
        frappe.throw(_(f"Row {item.idx}: Application Volume (per 100L) required for {item.item_code}"))
    
    if flt(item.custom_application_volume_per_10002000l) <= 0:
        frappe.throw(_(f"Row {item.idx}: Application Volume must be > 0 for {item.item_code}"))
    
    if not item.get("custom_volume"):
        frappe.throw(_(f"Row {item.idx}: Water Volume required for {item.item_code}"))
    
    if item.get("custom_area_to_spray"):
        frappe.throw(_(f"Row {item.idx}: Remove Area to Spray for Per 100L items"))

# You can add more utility functions here as needed
# For example:

def jinja_methods():
    """Custom Jinja methods for templates"""
    return {
        # Add your custom template methods here
        # "method_name": method_function,
    }

def jinja_filters():
    """Custom Jinja filters for templates"""
    return {
        # Add your custom template filters here
        # "filter_name": filter_function,
    }

# Example: Additional utility functions you might need
def get_greenhouse_capacity(greenhouse_name):
    """Get the capacity of a specific greenhouse"""
    # Your logic here
    pass

def calculate_fertilizer_requirement(area, crop_type):
    """Calculate fertilizer requirement based on area and crop"""
    # Your logic here
    pass


#material request
# upande_timaflor/utils.py

import json
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt


@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
    """Create a new Material Request from an existing Material Request"""
    
    def update_item(obj, target, source_parent):
        # Calculate remaining quantity that hasn't been ordered yet
        remaining_qty = flt(obj.stock_qty) - flt(obj.ordered_qty or 0)
        if remaining_qty > 0:
            target.qty = remaining_qty / (obj.conversion_factor or 1)
            target.stock_qty = remaining_qty
        else:
            target.qty = 0
            target.stock_qty = 0
    
    def set_missing_values(source, target):
        target.run_method("set_missing_values")
        # Clear the source material request reference to avoid circular references
        for item in target.items:
            item.material_request = None
            item.material_request_item = None

    def select_item(d):
        # Only include items that haven't been fully ordered
        return flt(d.ordered_qty or 0) < flt(d.stock_qty or 0)

    doclist = get_mapped_doc(
        "Material Request",
        source_name,
        {
            "Material Request": {
                "doctype": "Material Request",
                "validation": {
                    "docstatus": ["=", 1]
                },
            },
            "Material Request Item": {
                "doctype": "Material Request Item",
                "field_map": {
                    "parent": "source_material_request",
                    "name": "source_material_request_item",
                },
                "postprocess": update_item,
                "condition": select_item,
            },
        },
        target_doc,
        set_missing_values,
    )

    return doclist
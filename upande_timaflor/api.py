import frappe
import json

@frappe.whitelist()
def mark_items_po_created(item_names):
    if isinstance(item_names, str):
        item_names = json.loads(item_names)
    for name in item_names:
        frappe.db.set_value("Material Request Item", name, "custom_po_created", 1)
    frappe.db.commit()

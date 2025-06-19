import frappe

def execute():
    """Add target field to Chemical Sprays child table"""
    
    # Check if the field already exists
    if not frappe.db.exists("Custom Field", {"dt": "Chemical Sprays", "fieldname": "target"}):
        # Create the custom field
        custom_field = frappe.new_doc("Custom Field")
        custom_field.dt = "Chemical Sprays"
        custom_field.fieldname = "target"
        custom_field.label = "Target"
        custom_field.fieldtype = "Data"
        custom_field.insert()
        
        frappe.db.commit()
        print("Added target field to Chemical Sprays")
    else:
        print("Target field already exists in Chemical Sprays") 
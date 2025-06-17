import frappe
from frappe import _

def before_submit_material_request(doc, method=None):
    """
    Triggered before Material Request submission.
    Automatically sets the 'custom_approver' field to the farm manager linked to the source warehouse,
    ensuring only the correct manager can approve.
    """
    warehouse = None

    # Determine warehouse based on material request type
    if doc.material_request_type == "Material Issue":
        warehouse = doc.set_from_warehouse
    elif doc.material_request_type == "Material Transfer":
        warehouse = doc.set_warehouse

    if not warehouse:
        frappe.log_error(f"No warehouse specified for Material Request Type: {doc.material_request_type}", "Material Request Notification")
        return  # Exit if warehouse not set

    # Get farm linked to the warehouse
    farm = frappe.db.get_value("Warehouse", warehouse, "farm")
    if not farm:
        frappe.log_error(f"No Farm linked to Warehouse: {warehouse}", "Material Request Notification")
        return  # Exit if no farm linked

    try:
        farm_doc = frappe.get_doc("Farm", farm)
        manager = farm_doc.manager

        if not manager:
            frappe.log_error(f"No manager set for Farm: {farm}", "Material Request Notification")
            return

        # Automatically set the custom_approver field to the farm manager
        doc.custom_approver = manager
        frappe.log_error(f"'custom_approver' set to manager {manager} for Material Request {doc.name}", "Material Request Notification")

        # Set flag for client-side to make the field read-only
        doc.set_onload("approver_read_only", True)

    except Exception as ex:
        frappe.log_error(f"Error fetching Farm or manager: {ex}", "Material Request Notification")
        raise


def validate_material_request(doc, method=None):
    """
    Validates that the selected approver is either the farm manager or assistant manager
    linked to the source warehouse's farm.
    """
    warehouse = None

    if doc.material_request_type == "Material Issue":
        warehouse = doc.set_from_warehouse
    elif doc.material_request_type == "Material Transfer":
        warehouse = doc.set_warehouse

    if not warehouse:
        return  # No warehouse, no validation needed

    farm = frappe.db.get_value("Warehouse", warehouse, "farm")
    if not farm:
        return  # No farm, no validation needed

    try:
        farm_doc = frappe.get_doc("Farm", farm)
        manager = farm_doc.manager
        assistant_manager = farm_doc.assistant_manager

        allowed_approvers = [mgr for mgr in [manager, assistant_manager] if mgr]

        if doc.custom_approver not in allowed_approvers:
            frappe.throw(_(
                "Invalid Approver: {0}. Only the Farm Manager ({1}) or Assistant Manager ({2}) can approve this request."
            ).format(doc.custom_approver or "None", manager or "None", assistant_manager or "None"))

    except Exception as ex:
        frappe.log_error(f"Error during approver validation: {ex}", "Material Request Notification")
        raise


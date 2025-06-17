import frappe
from frappe import _

def on_update(doc, method):
    """Triggered when a Material Request is saved"""

    frappe.log_error("Material Request Script Triggered", "Material Request Notification")

    try:
        # Log document details
        frappe.log_error(f"Material Request: {doc.name}, Type: {doc.material_request_type}, Status: {doc.docstatus}", "Material Request Notification")

        warehouse = None

        # Determine warehouse based on material request type
        if doc.material_request_type == "Material Issue":
            warehouse = doc.set_from_warehouse
            frappe.log_error(f"Material Issue: From Warehouse = {warehouse}", "Material Request Notification")
        elif doc.material_request_type == "Material Transfer":
            warehouse = doc.set_warehouse
            frappe.log_error(f"Material Transfer: To Warehouse = {warehouse}", "Material Request Notification")

        if not warehouse:
            frappe.log_error(f"No warehouse specified for Material Request Type: {doc.material_request_type}", "Material Request Notification")
            return

        # Get farm associated with the warehouse
        farm = frappe.db.get_value("Warehouse", warehouse, "farm")
        if not farm:
            frappe.log_error(f"No farm associated with warehouse: {warehouse}", "Material Request Notification")
            return

        frappe.log_error(f"Farm: {farm} found for Warehouse: {warehouse}", "Material Request Notification")

        try:
            farm_doc = frappe.get_doc("Farm", farm)
            manager = farm_doc.manager
            assistant_manager = farm_doc.assistant_manager

            frappe.log_error(f"Farm Manager: {manager}, Assistant Manager: {assistant_manager}", "Material Request Notification")

            recipients = []

            if doc.material_request_type == "Material Transfer":
                # Only notify the target warehouse manager for transfers
                if manager:
                    recipients.append(manager)
                    frappe.log_error(f"Material Transfer: Adding manager {manager} to recipients", "Material Request Notification")
                else:
                    frappe.log_error("Material Transfer: No manager found for target warehouse", "Material Request Notification")
            else:
                # Notify both manager and assistant manager for other types
                if manager:
                    recipients.append(manager)
                    frappe.log_error(f"Adding manager {manager} to recipients", "Material Request Notification")
                if assistant_manager:
                    recipients.append(assistant_manager)
                    frappe.log_error(f"Adding assistant manager {assistant_manager} to recipients", "Material Request Notification")

            if not recipients:
                frappe.log_error("No recipients found for notification", "Material Request Notification")
                return

            frappe.log_error(f"Recipients: {recipients}", "Material Request Notification")

            subject = f"Material Request {doc.name} ({doc.material_request_type})"

            if doc.material_request_type == "Material Transfer":
                message = f"""A new Material Request {doc.name} of type {doc.material_request_type} has been created for your warehouse.
From: {doc.set_from_warehouse or "N/A"}
To: {doc.set_warehouse or "N/A"}

Materials are being transferred TO your warehouse. Please review and approve this request."""
            else:
                message = f"""A new Material Request {doc.name} of type {doc.material_request_type} has been created.
From: {doc.set_from_warehouse or "N/A"}
To: {doc.set_warehouse or "N/A"}

Please review and approve it if it concerns your farm."""

            # Send email notification
            try:
                frappe.sendmail(
                    recipients=recipients,
                    subject=subject,
                    message=message.replace("\n", "<br>"),
                    now=True
                )
                frappe.log_error("Email sent successfully", "Material Request Notification")
            except Exception as e:
                frappe.log_error(f"Error sending email: {e}", "Material Request Notification")

            # Create alternative notifications (ToDo, Comment, Realtime)
            for user in recipients:
                try:
                    # Check if user exists
                    if not frappe.db.exists("User", user):
                        frappe.log_error(f"User {user} does not exist", "Material Request Notification")
                        continue

                    # Create ToDo
                    try:
                        todo = frappe.new_doc("ToDo")
                        todo.description = subject
                        todo.reference_type = doc.doctype
                        todo.reference_name = doc.name
                        todo.allocated_to = user
                        todo.status = "Open"
                        todo.priority = "Medium"
                        todo.date = frappe.utils.today()
                        todo.insert(ignore_permissions=True)
                        frappe.db.commit()  # Commit after each ToDo creation
                        frappe.log_error(f"ToDo created for {user}: {todo.name}", "Material Request Notification")
                    except Exception as e:
                        frappe.log_error(f"Error creating ToDo for {user}: {e}", "Material Request Notification")

                    # Create Comment
                    try:
                        comment = frappe.new_doc("Comment")
                        comment.comment_type = "Info"
                        comment.reference_doctype = doc.doctype
                        comment.reference_name = doc.name
                        comment.content = f"<b>Notification:</b> {subject}<br><br>{message.replace(chr(10), '<br>')}"
                        comment.insert(ignore_permissions=True)
                        frappe.db.commit()  # Commit after each Comment creation
                        frappe.log_error(f"Comment created for {user}: {comment.name}", "Material Request Notification")
                    except Exception as e:
                        frappe.log_error(f"Error creating Comment for {user}: {e}", "Material Request Notification")

                    # Send Realtime Notification
                    try:
                        frappe.publish_realtime(
                            event="msgprint",
                            message=f"New {doc.material_request_type}: {doc.name}",
                            user=user
                        )
                        frappe.log_error(f"Realtime notification sent to {user}", "Material Request Notification")
                    except Exception as e:
                        frappe.log_error(f"Error sending realtime notification to {user}: {e}", "Material Request Notification")

                except Exception as e:
                    frappe.log_error(f"Error processing notifications for user {user}: {e}", "Material Request Notification")
                    import traceback
                    frappe.log_error(f"Traceback: {traceback.format_exc()}", "Material Request Notification")

        except Exception as e:
            frappe.log_error(f"Error retrieving farm document: {e}", "Material Request Notification")
            import traceback
            frappe.log_error(f"Traceback: {traceback.format_exc()}", "Material Request Notification")

    except Exception as e:
        frappe.log_error(f"Unexpected error: {e}", "Material Request Notification")
        import traceback
        frappe.log_error(f"Traceback: {traceback.format_exc()}", "Material Request Notification")

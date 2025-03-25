import frappe
from frappe import _

@frappe.whitelist()
def get_average_consumption(item, days_averaged):
    """
    Fetch average consumption of an item over selected days with enhanced error handling
    """
    # Validate inputs
    if not item or not days_averaged:
        frappe.throw(_("Item and Days Averaged are required"))
    
    # Convert days_averaged to integer
    try:
        days_averaged = int(days_averaged)
    except ValueError:
        frappe.throw(_("Days Averaged must be a valid integer"))
    
    # Calculate start date
    start_date = frappe.utils.add_days(frappe.utils.today(), -days_averaged)
    
    # Debug print
    frappe.log_error(f"Calculating average for item: {item}, start_date: {start_date}")
    
    # Query total consumption 
    consumption_query = """
        SELECT 
            IFNULL(SUM(
                CASE 
                    WHEN voucher_type = 'Stock Entry' THEN actual_qty 
                    WHEN voucher_type = 'Sales Invoice' THEN -actual_qty 
                    ELSE actual_qty 
                END
            ), 0) as total_consumption
        FROM tabStock Ledger Entry
        WHERE 
            item_code = %(item)s
            AND posting_date >= %(start_date)s
            AND is_cancelled = 0
    """
    
    try:
        result = frappe.db.sql(
            consumption_query, 
            {"item": item, "start_date": start_date}, 
            as_dict=True
        )
        
        # Extract total consumption
        total_consumption = result[0]['total_consumption'] if result else 0
        
        # Calculate daily average
        daily_avg = total_consumption / days_averaged if days_averaged > 0 else 0
        
        # Debug print
        frappe.log_error(f"Total Consumption: {total_consumption}, Daily Average: {daily_avg}")
        
        return daily_avg
    
    except Exception as e:
        # Log any unexpected errors
        frappe.log_error(f"Error calculating average consumption: {str(e)}")
        frappe.throw(_("Error calculating average consumption: {0}").format(str(e)))
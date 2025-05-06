import frappe

def execute(filters=None):
    if not filters or not filters.get("rfq"):
        frappe.msgprint("Please select an RFQ.")
        return [], []

    rfq_name = filters["rfq"]

    # Get all items from the RFQ
    rfq_items = frappe.get_all(
        "Request for Quotation Item",
        filters={"parent": rfq_name},
        fields=["item_code", "item_name", "uom"],
        distinct=True
    )

    # Get Supplier Quotations linked to the RFQ
    supplier_quotes = frappe.db.sql("""
        SELECT 
            sq.supplier,
            sqi.item_code,
            sqi.rate
        FROM 
            `tabSupplier Quotation` sq
        INNER JOIN 
            `tabSupplier Quotation Item` sqi ON sq.name = sqi.parent
        WHERE 
            request_for_quotation = %s
        ORDER BY 
            sq.supplier
    """, rfq_name, as_dict=True)

    if not supplier_quotes:
        frappe.msgprint("No supplier quotations found.")
        return [], []

    # Determine unique supplier list
    suppliers = sorted(list({q["supplier"] for q in supplier_quotes}))
    supplier_columns = [{"label": s, "fieldname": s, "fieldtype": "Currency"} for s in suppliers]

    # Define columns
    columns = [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
    ] + supplier_columns

    # Map of (item_code, supplier) -> rate
    rate_map = {(q["item_code"], q["supplier"]): q["rate"] for q in supplier_quotes}

    # Build rows
    data = []
    for item in rfq_items:
        row = {
            "item_code": item.item_code,
            "item_name": item.item_name
        }
        for supplier in suppliers:
            row[supplier] = rate_map.get((item.item_code, supplier), None)
        data.append(row)

    return columns, data

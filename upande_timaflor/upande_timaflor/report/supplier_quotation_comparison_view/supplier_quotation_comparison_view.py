import frappe

def execute(filters=None):
    if not filters or not filters.get("rfq"):
        frappe.msgprint("Please select an RFQ.")
        return [], []

    rfq_name = filters["rfq"]

    # Get the default company currency
    company_currency = frappe.get_value("Company", None, "default_currency")

    # Get all items in the RFQ
    rfq_items = frappe.get_all(
        "Request for Quotation Item",
        filters={"parent": rfq_name},
        fields=["item_code", "item_name", "uom"],
        distinct=True
    )

    if not rfq_items:
        frappe.msgprint("No items found in the selected RFQ.")
        return [], []

    # Get supplier quotations related to this RFQ
    supplier_quotes = frappe.db.sql("""
        SELECT 
            sq.name AS quotation_name,
            sq.supplier,
            sq.currency,
            sqi.item_code,
            sqi.rate
        FROM `tabSupplier Quotation` sq
        INNER JOIN `tabSupplier Quotation Item` sqi ON sq.name = sqi.parent
        WHERE request_for_quotation = %s
    """, rfq_name, as_dict=True)

    if not supplier_quotes:
        frappe.msgprint("No supplier quotations found.")
        return [], []

    # Map supplier to their metadata
    supplier_meta = {}
    for quote in supplier_quotes:
        supplier = quote["supplier"]
        if supplier not in supplier_meta:
            supplier_meta[supplier] = {
                "currency": quote["currency"] if quote["currency"] else company_currency,
                "quotation_name": quote["quotation_name"]
            }

    suppliers = sorted(supplier_meta.keys())

    # Build dynamic columns
    columns = [
        {"label": "ITEM CODE", "fieldname": "item_code", "fieldtype": "Data", "width": 120},
        {"label": "ITEM NAME", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 80},
    ]

    for supplier in suppliers:
        quotation_name = supplier_meta[supplier]["quotation_name"]
        link = f"/app/supplier-quotation/{quotation_name}"
        columns.append({
            "label": f"""<a href="{link}" style="text-decoration:none;">{supplier}</a>""",
            "fieldname": supplier,
            "fieldtype": "HTML",
            "width": 220
        })

    # Map (item_code, supplier) → rate
    rate_map = {}
    for quote in supplier_quotes:
        rate_map[(quote.item_code, quote.supplier)] = {
            "rate": quote.rate,
            "currency": quote.currency if quote.currency else company_currency
        }

    # Prepare table rows
    data = []
    for item in rfq_items:
        row = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "uom": item.uom
        }

        item_rates = {
            supplier: rate_map.get((item.item_code, supplier), {}).get("rate")
            for supplier in suppliers
        }

        # Determine min and max rates (exclude None)
        valid_rates = [r for r in item_rates.values() if r is not None]
        min_rate = min(valid_rates) if valid_rates else None
        max_rate = max(valid_rates) if valid_rates else None

        # Add supplier-specific rate cells
        for supplier in suppliers:
            rate = item_rates[supplier]
            currency = supplier_meta[supplier]["currency"] or company_currency

            if rate is None:
                row[supplier] = ""
            else:
                # Determine color
                if rate == min_rate:
                    color = "green"
                elif rate == max_rate:
                    color = "red"
                else:
                    color = "black"

                formatted = f"{frappe.utils.fmt_money(rate, precision=2, currency=currency)}"



                row[supplier] = f"""<span style="color:{color};">{formatted}</span>"""

        data.append(row)

    return columns, data

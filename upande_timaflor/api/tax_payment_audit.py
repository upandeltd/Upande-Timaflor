# Tax Payment Audit - Script Report for ERPNext

import frappe

def execute(filters=None):
    columns = [
        {"label": "Tax Payment", "fieldname": "tax_payment", "fieldtype": "Link", "options": "Tax Payment", "width": 140},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Tax Type", "fieldname": "tax_type", "fieldtype": "Data", "width": 140},
        {"label": "Supplier", "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": "Invoice No", "fieldname": "supplier_invoice_no", "fieldtype": "Data", "width": 120},
        {"label": "Tax Amount", "fieldname": "tax_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Journal Entry", "fieldname": "journal_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 140},
        {"label": "PRN", "fieldname": "prn", "fieldtype": "Data", "width": 140}
    ]

    # Apply filters
    conditions = ""
    values = {}

    if filters:
        if filters.get("tax_type"):
            conditions += " AND tp.tax_type = %(tax_type)s"
            values["tax_type"] = filters["tax_type"]

        if filters.get("status"):
            conditions += " AND tpe.status = %(status)s"
            values["status"] = filters["status"]

        if filters.get("from_date"):
            conditions += " AND tp.posting_date >= %(from_date)s"
            values["from_date"] = filters["from_date"]

        if filters.get("to_date"):
            conditions += " AND tp.posting_date <= %(to_date)s"
            values["to_date"] = filters["to_date"]

    # Fetch data
    data = frappe.db.sql(f"""
        SELECT
            tp.name AS tax_payment,
            tp.posting_date,
            tp.tax_type,
            tpe.supplier_name,
            tpe.supplier_invoice_no,
            tpe.tax_amount,
            tpe.status,
            tpe.journal_entry,
            tpe.prn
        FROM `tabTax Payment` tp
        INNER JOIN `tabTax Payment Entry` tpe ON tpe.parent = tp.name
        WHERE tp.docstatus < 2 {conditions}
        ORDER BY tp.posting_date DESC, tp.name DESC
    """, values, as_dict=True)

    return columns, data

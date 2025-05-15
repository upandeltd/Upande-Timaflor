

import frappe
from frappe.utils import flt

def execute(filters=None):
    columns = [
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Supplier Invoice No", "fieldname": "supplier_invoice_no", "fieldtype": "Data", "width": 130},
        {"label": "ERP Invoice", "fieldname": "invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 150},
        {"label": "Detail", "fieldname": "detail", "fieldtype": "Data", "width": 200},
        {"label": "Account", "fieldname": "account", "fieldtype": "Data", "width": 200},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
        {"label": "Bank", "fieldname": "bank", "fieldtype": "Data", "width": 150},
        {"label": "Payment Entry", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 150},
    ]

    data = []

    invoices = frappe.get_all("Purchase Invoice",
        filters={
            "docstatus": 1,
            "posting_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
            "supplier": filters.get("supplier"),
        },
        fields=["name", "posting_date", "custom_invoice_number", "grand_total", "net_total"]
    )

    for inv in invoices:
        taxes = frappe.get_all("Purchase Taxes and Charges",
            filters={"parent": inv.name},
            fields=["account_head", "tax_amount"]
        )

        vat_16 = sum(t.tax_amount for t in taxes if "vat control" in (t.account_head or "").lower() and t.tax_amount > 0)
        total_before_withholding = inv.net_total + vat_16
        withholding_vat = sum(t.tax_amount for t in taxes if "withholding vat" in (t.account_head or "").lower())
        withholding_tax = sum(t.tax_amount for t in taxes if "withholding tax" in (t.account_head or "").lower())

        # Row: Total Before Withholding
        data.append({
            "posting_date": inv.posting_date,
            "supplier_invoice_no": inv.custom_invoice_number,
            "invoice": inv.name,
            "detail": "Total (Before Withholding)",
            "account": "",
            "amount": total_before_withholding
        })

        # Row: Withholding VAT
        for t in taxes:
            if "withholding vat" in (t.account_head or "").lower():
                data.append({
                    "posting_date": "",
                    "supplier_invoice_no": "",
                    "invoice": "",
                    "detail": "Withholding VAT",
                    "account": t.account_head,
                    "amount": t.tax_amount
                })

        # Row: Withholding Tax
        if withholding_tax:
            for t in taxes:
                if "withholding tax" in (t.account_head or "").lower():
                    data.append({
                        "posting_date": "",
                        "supplier_invoice_no": "",
                        "invoice": "",
                        "detail": "Withholding Tax",
                        "account": t.account_head,
                        "amount": t.tax_amount
                    })

        # Row: Bank & Payment Entry
        payments = frappe.get_all("Payment Entry Reference",
            filters={"reference_doctype": "Purchase Invoice", "reference_name": inv.name},
            fields=["parent"]
        )

        for p in payments:
            pe = frappe.get_doc("Payment Entry", p.parent)
            data.append({
                "posting_date": "",
                "supplier_invoice_no": "",
                "invoice": "",
                "detail": "Bank Payment",
                "account": pe.paid_from,
                "amount": pe.paid_amount,
                "bank": pe.paid_from,
                "payment_entry": pe.name
            })

        # Row: Withholding Payments (if paid separately)
        withholding_payments = frappe.get_all("Payment Entry",
            filters={"party_type": "Supplier", "party": filters.get("supplier"), "docstatus": 1},
            fields=["name", "paid_from", "paid_amount"]
        )

        for pe in withholding_payments:
            accounts = frappe.get_all("Payment Entry Account",
                filters={"parent": pe.name},
                fields=["account", "debit_in_account_currency"]
            )
            for a in accounts:
                if "withholding" in (a.account or "").lower():
                    data.append({
                        "posting_date": "",
                        "supplier_invoice_no": "",
                        "invoice": "",
                        "detail": "Withholding Payment",
                        "account": a.account,
                        "amount": a.debit_in_account_currency,
                        "bank": pe.paid_from,
                        "payment_entry": pe.name
                    })

    return columns, data

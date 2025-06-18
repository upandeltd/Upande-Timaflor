# ~/frappe-bench/apps/upande_timaflor/upande_timaflor/report/custom_general_ledger/custom_general_ledger.py

import frappe # type: ignore

def execute(filters=None):
    if not filters:
        filters = {}

    account = filters.get("account")
    if not account:
        return [], []

    data = get_ledger_data(account)

    columns = [
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Supplier Invoice No", "fieldname": "supplier_invoice", "fieldtype": "Data", "width": 150},
        {"label": "Supplier Name", "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": "Against Account", "fieldname": "against_account", "fieldtype": "Data", "width": 180},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 120},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 120},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 150},
    ]

    return columns, data

def get_ledger_data(account):
    entries = frappe.db.sql("""
        SELECT
            gle.posting_date,
            pi.custom_supplier_invoice_no AS supplier_invoice,
            supp.supplier_name,
            REPLACE(gle.against, CONCAT(' - ', SUBSTRING_INDEX(gle.against, ' - ', -1)), '') AS against_account,
            gle.credit,
            gle.debit,
            gle.voucher_no,
            gle.voucher_type
        FROM `tabGL Entry` gle
        LEFT JOIN `tabPurchase Invoice` pi ON gle.voucher_type = 'Purchase Invoice' AND gle.voucher_no = pi.name
        LEFT JOIN `tabSupplier` supp ON pi.supplier = supp.name
        WHERE gle.account = %s
        ORDER BY gle.posting_date, gle.creation
    """, (account,), as_dict=True)

    balance = 0
    for e in entries:
        balance += (e.debit - e.credit)
        e["balance"] = balance
        e["supplier_name"] = e["supplier_name"] or ""

    return entries

@frappe.whitelist()
def get_account_title(account):
    acc = frappe.get_doc("Account", account)
    if acc.account_type == "Payable":
        return "Supplier Accounts"
    elif acc.account_type == "Receivable":
        return "Customer Accounts"
    else:
        return acc.account_name

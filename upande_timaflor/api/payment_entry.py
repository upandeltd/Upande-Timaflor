# apps/upande_timaflor/upande_timaflor/api/payment_entry.py
import frappe # type: ignore
from erpnext.accounts.doctype.payment_entry.payment_entry import get_outstanding_invoices # type: ignore

@frappe.whitelist()
def get_supplier_outstanding_invoices(party_type, party, company):
    return get_outstanding_invoices(party_type, party, company)

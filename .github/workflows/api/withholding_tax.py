# apps/upande_timaflor/upande_timaflor/api/withholding_tax.py

import frappe

@frappe.whitelist()
def get_withholding_tax_entries(supplier):
    return frappe.db.sql("""
        SELECT je.name, je.total_debit AS amount
        FROM `tabJournal Entry` je
        JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
        WHERE je.docstatus = 1
        AND jea.party_type = 'Supplier'
        AND jea.party = %s
        AND jea.account LIKE '%%Withholding%%'
        AND NOT EXISTS (
            SELECT 1 FROM `tabPayment Entry Reference`
            WHERE reference_doctype = 'Journal Entry' AND reference_name = je.name
        )
    """, (supplier,), as_dict=True)

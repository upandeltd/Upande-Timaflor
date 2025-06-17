import frappe  # type: ignore
from frappe.utils import flt, nowdate  # type: ignore

@frappe.whitelist()
def fetch_tax_entries(docname):
    doc = frappe.get_doc("Tax Payment", docname)

    if not doc:
        frappe.throw(f"Tax Payment {docname} not found")

    frappe.msgprint("Server script is running")

    tax_account_map = {
        "VAT": "21020101 - VAT Control - TL",
        "WITHHOLDING VAT": "21020102 - Withholding VAT - TL",
        "WITHHOLDING Tax": "21020201 - Withholding Tax - TL"
    }

    account = tax_account_map.get(doc.tax_type)
    if not account:
        frappe.throw("Invalid tax type selected.")

    if not doc.from_date or not doc.to_date:
        frappe.throw("Please set From Date and To Date.")

    doc.set("tax_entries", [])

    gl_entries = frappe.db.sql("""
        SELECT
            gle.posting_date,
            gle.voucher_no,
            gle.voucher_type,
            gle.against,
            gle.credit,
            gle.debit,
            gle.account,
            pi.custom_invoice_number,
            pi.bill_no
        FROM `tabGL Entry` gle
        LEFT JOIN `tabPurchase Invoice` pi
            ON gle.voucher_type = 'Purchase Invoice'
            AND gle.voucher_no = pi.name
        WHERE gle.account = %s
          AND gle.posting_date BETWEEN %s AND %s
        ORDER BY gle.posting_date ASC
    """, (account, doc.from_date, doc.to_date), as_dict=True)

    frappe.msgprint(f"GL Entries found: {len(gl_entries)}")

    for entry in gl_entries:
        supplier = entry.against
        invoice = entry.bill_no
        credit = flt(entry.credit)
        debit = flt(entry.debit)
        balance = credit - debit

        status = "Settled" if round(balance, 2) <= 0 else "Unsettled"

        doc.append("tax_entries", {
            "supplier_name": supplier,
            "supplier_invoice_no": invoice,
            "tax_amount": balance,
            "status": status
        })

    doc.save()

@frappe.whitelist()
def create_tax_payment_journal_entries(docname):
    doc = frappe.get_doc("Tax Payment", docname)

    tax_accounts = {
        "VAT": {
            "from": "21020101 - VAT Control - TL"
        },
        "WITHHOLDING VAT": {
            "from": "21020102 - Withholding VAT - TL"
        },
        "WITHHOLDING Tax": {
            "from": "21020201 - Withholding Tax - TL"
        }
    }

    accounts = tax_accounts.get(doc.tax_type)
    if not accounts:
        frappe.throw("Invalid tax type configuration.")

    # ✅ Get the company account from the selected Bank Account
    if not doc.bank_account:
        frappe.throw("Please select a Bank Account in the Tax Payment form.")

    bank_account_doc = frappe.get_doc("Bank Account", doc.bank_account)
    company_account = bank_account_doc.account

    if not company_account:
        frappe.throw(f"The selected Bank Account '{doc.bank_account}' does not have a Company Account set.")

    created_entries = 0

    for row in doc.tax_entries:
        if not row.select_for_payment or row.status == "Settled":
            continue

        if row.journal_entry:
            continue

        je = frappe.new_doc("Journal Entry")
        je.posting_date = nowdate()
        je.voucher_type = "Journal Entry"
        je.user_remark = f"Tax Payment for {row.supplier_invoice_no or 'N/A'} ({doc.tax_type})"

        # Debit the tax account (clearing the liability)
        je.append("accounts", {
            "account": accounts["from"],
            "debit_in_account_currency": flt(row.tax_amount),
            "reference_type": "Purchase Invoice" if row.supplier_invoice_no else "",
            "reference_name": row.supplier_invoice_no or ""
        })

        # Credit the bank account (actual payment to KRA)
        je.append("accounts", {
            "account": company_account,
            "credit_in_account_currency": flt(row.tax_amount),
            #"party_type": "Supplier",
            #"party": "KENYA REVENUE AUTHORITY"
        })

        je.save()
        je.submit()

        row.journal_entry = je.name
        row.status = "Settled"
        created_entries += 1

    doc.save()

    return f"{created_entries} Journal Entries created."

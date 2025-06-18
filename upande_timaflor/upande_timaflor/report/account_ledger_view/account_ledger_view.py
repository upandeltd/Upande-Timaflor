from __future__ import unicode_literals
import frappe
from frappe.utils import flt, nowdate, add_months

"""
Account Ledger View  
————————————————
• Summary view (grouped by root type) with clickable account names.  
• Ledger drill‑down when the **account** filter is set.  
• Root‑type headers rendered with a light‑grey background.
"""

def execute(filters=None):
    filters = frappe._dict(filters or {})
    company = frappe.defaults.get_user_default("Company")
    company_currency = frappe.get_cached_value("Company", company, "default_currency")

    # Default dates → current month
    filters.setdefault("from_date", add_months(nowdate(), -1)[:8] + "01")
    filters.setdefault("to_date", nowdate())

    # ──────────────── SUMMARY VIEW ────────────────
    if not filters.get("account"):
        cols = get_summary_columns(company_currency)
        data = get_account_summaries(filters)
        return cols, data

    # ──────────────── LEDGER VIEW ────────────────
    cols = get_ledger_columns(filters["account"], company_currency)
    data = get_ledger_entries(filters, company_currency)

    acct_name = frappe.get_cached_value("Account", filters["account"], "account_name")

    report_summary = [{
        "label": f"Ledger – {acct_name}",
        "value": "",
        "indicator": "blue"
    }]

    return cols, data, None, None, report_summary

# ═════════════════════════════════════════════════════════════════════
# SUMMARY VIEW HELPERS
# ═════════════════════════════════════════════════════════════════════

def get_summary_columns(currency):
    return [
        {"label": "Account Number", "fieldname": "account_number", "HTML": "Data", "width": 140},
        {"label": "Account Name", "fieldname": "account_name", "fieldtype": "HTML", "width": 260},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Float", "width": 110},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Float", "width": 110},
        {"label": "Balance", "fieldname": "balance", "fieldtype": "Float", "width": 120},
    ]

def get_account_summaries(filters):
    rows = frappe.db.sql("""
        SELECT
            a.name AS account,
            a.account_number,
            a.account_name,
            a.parent_account,
            a.root_type,
            CASE WHEN a.parent_account IS NULL THEN 0 ELSE 1 END AS indent,
            SUM(gle.debit) AS debit,
            SUM(gle.credit) AS credit,
            SUM(gle.debit - gle.credit) AS balance
        FROM `tabGL Entry` gle
        JOIN `tabAccount` a ON a.name = gle.account
        WHERE gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND a.account_number is not null
        GROUP BY gle.account
        ORDER BY FIELD(a.root_type,'Asset','Liability','Equity','Income','Expense'),
                 a.parent_account,
                 a.account_number
    """, filters, as_dict=True)

    rows = [r for r in rows if any([flt(r.debit), flt(r.credit), flt(r.balance)])]

    grouped, current = [], None
    debit_t = credit_t = balance_t = 0

    for r in rows:
        if r.root_type != current:
            if current is not None:
                grouped.append({
                    "account_name": f"Total {current}",
                    "debit": debit_t,
                    "credit": credit_t,
                    "balance": balance_t,
                    "indent": 0
                })
            grouped.append({
                "account_name": f"<span style='background:#f5f5f5;font-weight:600;padding:2px 6px;border-radius:4px'>{r.root_type}</span>",
                "indent": 0,
                "is_section": 1
            })
            current = r.root_type
            debit_t = credit_t = balance_t = 0

        r.indent = 1
        r.account_number = f'<a data-ledger-account="{r.account}" style="color: var(--text-on-white)" href="#">{r.account_number}</a>'

        r.account_name = f"<a href='#' data-ledger-account='{r.account}'>{frappe.utils.escape_html(r.account_name)}</a>"

        debit_t += flt(r.debit)
        credit_t += flt(r.credit)
        balance_t += flt(r.balance)

        grouped.append(r)

    if current is not None:
        grouped.append({
            "account_name": f"Total {current}",
            "debit": debit_t,
            "credit": credit_t,
            "balance": balance_t,
            "indent": 0
        })

    return grouped

# ═════════════════════════════════════════════════════════════════════
# LEDGER VIEW HELPERS
# ═════════════════════════════════════════════════════════════════════

def get_ledger_columns(account, company_currency):
    acct_currency = frappe.get_cached_value("Account", account, "account_currency")
    same_curr = (acct_currency == company_currency)

    cols = [
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Data", "width": 260},
        {"label": "CU Invoice No", "fieldname": "cu_invoice_no", "fieldtype": "Data", "width": 140},
        {"label": f"Debit ({company_currency})", "fieldname": "debit", "fieldtype": "Float", "options": company_currency, "width": 110},
        {"label": f"Credit ({company_currency})", "fieldname": "credit", "fieldtype": "Float", "options": company_currency, "width": 110},
        {"label": f"Balance ({company_currency})", "fieldname": "balance", "fieldtype": "Float", "options": company_currency, "width": 120},
    ]

    if not same_curr:
        cols += [
            {"label": f"Debit ({acct_currency})", "fieldname": "debit_acc", "fieldtype": "Float", "options": acct_currency, "width": 110},
            {"label": f"Credit ({acct_currency})", "fieldname": "credit_acc", "fieldtype": "Float", "options": acct_currency, "width": 110},
            {"label": f"Balance ({acct_currency})", "fieldname": "balance_acc", "fieldtype": "Float", "options": acct_currency, "width": 130},
            {"label": "Rate", "fieldname": "rate", "fieldtype": "Float", "width": 60},
        ]

    cols.append({"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 170})
    return cols

def get_ledger_entries(filters, company_currency):
    conditions = []
    if filters.get("account"):
        conditions.append("gle.account = %(account)s")
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("gle.posting_date BETWEEN %(from_date)s AND %(to_date)s")

    condition_str = " AND ".join(conditions)

    entries = frappe.db.sql(f"""
        SELECT 
            gle.posting_date,
            gle.debit,
            gle.credit,
            gle.voucher_type,
            gle.voucher_no,
            gle.account_currency,
            gle.debit_in_account_currency AS debit_acc,
            gle.credit_in_account_currency AS credit_acc,
            gle.account,
            gle.against_voucher_type,
            gle.against_voucher,
            gle.party_type,
            gle.party,
            gle.remarks,
            pi.bill_no AS cu_invoice_no,
            pi.supplier AS supplier,
            CASE 
                WHEN gle.debit_in_account_currency > 0 THEN gle.debit_in_account_currency / gle.debit
                WHEN gle.credit_in_account_currency > 0 THEN gle.credit_in_account_currency / gle.credit
                ELSE 1
            END AS rate
        FROM `tabGL Entry` gle
        LEFT JOIN `tabPurchase Invoice` pi ON pi.name = gle.voucher_no AND gle.voucher_type = 'Purchase Invoice'
        WHERE {condition_str}
        ORDER BY gle.posting_date, gle.creation
    """, filters, as_dict=True)

    # Fallback: Add supplier and cu_invoice_no for Journal Entries
    for e in entries:
        if e.voucher_type == "Journal Entry":
            if not e.get("supplier"):
                e["supplier"] = frappe.db.get_value("Journal Entry Account", {
                    "parent": e.voucher_no,
                    "account": e.account,
                    "party_type": "Supplier"
                }, "party") or ""

            if not e.get("cu_invoice_no"):
                e["cu_invoice_no"] = frappe.db.get_value("Journal Entry", e.voucher_no, "bill_no") or ""

    # Running balance
    balance = 0
    balance_acc = 0
    for e in entries:
        balance += flt(e.debit) - flt(e.credit)
        e["balance"] = balance

        if e.get("debit_acc") or e.get("credit_acc"):
            balance_acc += flt(e.get("debit_acc")) - flt(e.get("credit_acc"))
            e["balance_acc"] = balance_acc

    return entries

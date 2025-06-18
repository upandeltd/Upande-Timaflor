# api.py - Enhanced Server methods for Tax Payment with improved Journal Entry handling

import frappe
from frappe import _
from frappe.utils import flt, nowdate
import re # Import the re module for regular expressions
from erpnext.accounts.utils import get_balance_on

@frappe.whitelist()
def get_pending_tax_entries(tax_account, company):
    """
    Get all pending (unpaid) tax entries for a specific tax account.
    Enhanced to better handle Journal Entry supplier information through supplier control account.
    """
    
    # Get paid entries from existing Tax Payment documents
    paid_entries = frappe.db.sql("""
        SELECT DISTINCT tpe.invoice
        FROM `tabTax Payment Entry` tpe
        INNER JOIN `tabTax Payment` tp ON tpe.parent = tp.name
        WHERE tp.docstatus = 1 
        AND tpe.payment_status = 'Paid'
        AND tp.tax_account = %s
        AND tp.company = %s
    """, (tax_account, company), as_dict=True)
    
    paid_entry_list = [d.invoice for d in paid_entries] if paid_entries else []
    
    paid_entries_condition = ""
    if paid_entry_list:
        paid_entries_str = "', '".join(paid_entry_list)
        paid_entries_condition = f"AND gle.voucher_no NOT IN ('{paid_entries_str}')"
    
    # Enhanced query with better Journal Entry handling - excludes payment entries
    query = f"""
        SELECT DISTINCT
            gle.voucher_no as invoice,
            CASE 
                WHEN gle.voucher_type = 'Purchase Invoice' THEN pi.supplier
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.supplier
                ELSE NULL 
            END as supplier,
            CASE 
                WHEN gle.voucher_type = 'Purchase Invoice' THEN pi.bill_no
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.bill_no
                ELSE NULL 
            END as bill_no,
            CASE 
                WHEN gle.voucher_type = 'Purchase Invoice' THEN pi.supplier_name
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.supplier_name
                ELSE NULL 
            END as supplier_name,
            gle.posting_date,
            gle.remarks,
            SUM(gle.debit - gle.credit) as balance_amount_raw,
            ABS(SUM(gle.debit - gle.credit)) as outstanding_amount,
            CASE 
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.purchase_invoice_id
                ELSE NULL 
            END as linked_purchase_invoice_from_je
        FROM `tabGL Entry` gle
        LEFT JOIN `tabPurchase Invoice` pi ON gle.voucher_no = pi.name AND gle.voucher_type = 'Purchase Invoice'
        LEFT JOIN (
            SELECT 
                je_supplier.parent as journal_entry,
                je_supplier.party as supplier,
                sup.supplier_name,
                je_supplier.reference_name as purchase_invoice_id,
                pi_ref.bill_no
            FROM `tabJournal Entry Account` je_supplier
            LEFT JOIN `tabSupplier` sup ON je_supplier.party = sup.name
            LEFT JOIN `tabPurchase Invoice` pi_ref ON je_supplier.reference_name = pi_ref.name
            WHERE je_supplier.party_type = 'Supplier'
            AND je_supplier.account_type = 'Payable'
        ) supplier_info ON gle.voucher_no = supplier_info.journal_entry AND gle.voucher_type = 'Journal Entry'
        WHERE gle.account = %s 
        AND gle.company = %s
        AND gle.is_cancelled = 0
        AND (
            (gle.voucher_type = 'Purchase Invoice' AND pi.docstatus = 1) OR
            (gle.voucher_type = 'Journal Entry' AND EXISTS (SELECT 1 FROM `tabJournal Entry` je WHERE je.name = gle.voucher_no AND je.docstatus = 1)
             AND NOT EXISTS (
                 SELECT 1 FROM `tabJournal Entry Account` jea_bank 
                 WHERE jea_bank.parent = gle.voucher_no 
                 AND jea_bank.account_type IN ('Bank', 'Cash')
                 AND jea_bank.credit_in_account_currency > 0
                 AND EXISTS (
                     SELECT 1 FROM `tabJournal Entry Account` jea_tax
                     WHERE jea_tax.parent = gle.voucher_no
                     AND jea_tax.account = %s
                     AND jea_tax.debit_in_account_currency > 0
                 )
             ))
        )
        {paid_entries_condition}
        GROUP BY gle.voucher_no, gle.posting_date, supplier, bill_no, supplier_name, gle.remarks, linked_purchase_invoice_from_je
        HAVING ABS(SUM(gle.debit - gle.credit)) > 0.01
        ORDER BY gle.posting_date DESC
    """
    
    try:
        result = frappe.db.sql(query, (tax_account, company, tax_account), as_dict=True)
        
        validated_results = []
        for entry in result:
            # Skip if this looks like a tax payment entry
            if entry.invoice.startswith('ACC-JV') and is_tax_payment_entry(entry.invoice, tax_account):
                continue
                
            actual_balance = get_voucher_tax_balance(entry.invoice, tax_account)
            
            if abs(actual_balance) > 0.01:
                entry.balance_amount = actual_balance
                entry.outstanding_amount = abs(actual_balance)
                entry.is_withholding_tax = actual_balance < 0
                entry.account_type = "Withholding Tax" if actual_balance < 0 else "VAT/Output Tax"
                entry.tax_amount = abs(actual_balance)
                
                # Enhanced parsing logic
                entry = enhance_entry_with_invoice_info(entry)
                
                validated_results.append(entry)
        
        return validated_results
        
    except Exception as e:
        frappe.log_error(f"Error in get_pending_tax_entries: {str(e)}")
        frappe.throw(_("Error fetching pending tax entries. Please contact administrator."))

@frappe.whitelist()
def get_withholding_tax_entries_only(tax_account, company):
    """
    Enhanced withholding tax entries fetcher with better Journal Entry handling.
    """
    
    paid_entries = frappe.db.sql("""
        SELECT DISTINCT tpe.invoice
        FROM `tabTax Payment Entry` tpe
        INNER JOIN `tabTax Payment` tp ON tpe.parent = tp.name
        WHERE tp.docstatus = 1 
        AND tpe.payment_status = 'Paid'
        AND tp.tax_account = %s
        AND tp.company = %s
    """, (tax_account, company), as_dict=True)
    
    paid_entry_list = [d.invoice for d in paid_entries] if paid_entries else []
    
    paid_entries_condition = ""
    if paid_entry_list:
        paid_entries_str = "', '".join(paid_entry_list)
        paid_entries_condition = f"AND gle.voucher_no NOT IN ('{paid_entries_str}')"
    
    # Enhanced query for withholding tax with better Journal Entry support - excludes payment entries
    query = f"""
        SELECT DISTINCT
            gle.voucher_no as invoice,
            CASE 
                WHEN gle.voucher_type = 'Purchase Invoice' THEN pi.supplier
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.supplier
                ELSE NULL 
            END as supplier,
            CASE 
                WHEN gle.voucher_type = 'Purchase Invoice' THEN pi.bill_no
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.bill_no
                ELSE NULL 
            END as bill_no,
            CASE 
                WHEN gle.voucher_type = 'Purchase Invoice' THEN pi.supplier_name
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.supplier_name
                ELSE NULL 
            END as supplier_name,
            gle.posting_date,
            gle.remarks,
            ABS(SUM(gle.debit - gle.credit)) as outstanding_amount,
            ABS(SUM(gle.debit - gle.credit)) as tax_amount,
            SUM(gle.debit - gle.credit) as balance_amount_raw,
            CASE 
                WHEN gle.voucher_type = 'Journal Entry' THEN supplier_info.purchase_invoice_id
                ELSE NULL 
            END as linked_purchase_invoice_from_je
        FROM `tabGL Entry` gle
        LEFT JOIN `tabPurchase Invoice` pi ON gle.voucher_no = pi.name AND gle.voucher_type = 'Purchase Invoice'
        LEFT JOIN (
            SELECT 
                je_supplier.parent as journal_entry,
                je_supplier.party as supplier,
                sup.supplier_name,
                je_supplier.reference_name as purchase_invoice_id,
                pi_ref.bill_no
            FROM `tabJournal Entry Account` je_supplier
            LEFT JOIN `tabSupplier` sup ON je_supplier.party = sup.name
            LEFT JOIN `tabPurchase Invoice` pi_ref ON je_supplier.reference_name = pi_ref.name
            WHERE je_supplier.party_type = 'Supplier'
            AND je_supplier.account_type = 'Payable'
        ) supplier_info ON gle.voucher_no = supplier_info.journal_entry AND gle.voucher_type = 'Journal Entry'
        WHERE gle.account = %s 
        AND gle.company = %s
        AND gle.is_cancelled = 0
        AND (
            (gle.voucher_type = 'Purchase Invoice' AND pi.docstatus = 1) OR
            (gle.voucher_type = 'Journal Entry' AND EXISTS (SELECT 1 FROM `tabJournal Entry` je WHERE je.name = gle.voucher_no AND je.docstatus = 1)
             AND NOT EXISTS (
                 SELECT 1 FROM `tabJournal Entry Account` jea_bank 
                 WHERE jea_bank.parent = gle.voucher_no 
                 AND jea_bank.account_type IN ('Bank', 'Cash')
                 AND jea_bank.credit_in_account_currency > 0
                 AND EXISTS (
                     SELECT 1 FROM `tabJournal Entry Account` jea_tax
                     WHERE jea_tax.parent = gle.voucher_no
                     AND jea_tax.account = %s
                     AND jea_tax.debit_in_account_currency > 0
                 )
             ))
        )
        {paid_entries_condition}
        GROUP BY gle.voucher_no, gle.posting_date, supplier, bill_no, supplier_name, gle.remarks, linked_purchase_invoice_from_je
        HAVING SUM(gle.debit - gle.credit) < -0.01
        ORDER BY gle.posting_date DESC
    """
    
    try:
        result = frappe.db.sql(query, (tax_account, company, tax_account), as_dict=True)
        
        for entry in result:
            # Skip if this looks like a tax payment entry
            if entry.invoice.startswith('ACC-JV') and is_tax_payment_entry(entry.invoice, tax_account):
                continue
                
            entry.is_withholding_tax = True
            entry.account_type = "Withholding Tax"
            entry.payment_direction = "To Tax Authority"
            entry.balance_amount = entry.balance_amount_raw
            
            # Enhanced parsing logic
            entry = enhance_entry_with_invoice_info(entry)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in get_withholding_tax_entries_only: {str(e)}")
        frappe.throw(_("Error fetching withholding tax entries. Please contact administrator."))

def enhance_entry_with_invoice_info(entry):
    """
    Enhanced function to extract Purchase Invoice and Bill information from various sources.
    """
    # First, check if we got the info directly from the Journal Entry reference
    if entry.get('linked_purchase_invoice_from_je'):
        entry.linked_purchase_invoice = entry.linked_purchase_invoice_from_je
        return entry
    
    # If not, try parsing from remarks
    remarks = entry.get('remarks', '')
    if remarks:
        # Try multiple regex patterns for Purchase Invoice ID
        pi_patterns = [
            r"Purchase Invoice ([A-Z0-9-]+)",
            r"PI[:\s]*([A-Z0-9-]+)",
            r"Invoice[:\s]*([A-Z0-9-]+)",
            r"Ref[:\s]*([A-Z0-9-]+)"
        ]
        
        for pattern in pi_patterns:
            pi_match = re.search(pattern, remarks, re.IGNORECASE)
            if pi_match:
                entry.linked_purchase_invoice = pi_match.group(1)
                break
        
        # Try multiple patterns for Bill Number
        bill_patterns = [
            r"Bill[:\s]*([A-Z0-9]+)",
            r"Bill No[:\s]*([A-Z0-9]+)",
            r"Bill Number[:\s]*([A-Z0-9]+)",
            r"Supplier Invoice[:\s]*([A-Z0-9]+)"
        ]
        
        for pattern in bill_patterns:
            bill_match = re.search(pattern, remarks, re.IGNORECASE)
            if bill_match:
                entry.linked_bill_no = bill_match.group(1)
                break
    
    # If still no supplier info and this is a Journal Entry, try alternative method
    if not entry.get('supplier') and entry.get('invoice', '').startswith('ACC-JV'):
        supplier_from_je = get_supplier_from_journal_entry(entry.invoice)
        if supplier_from_je:
            entry.supplier = supplier_from_je.get('supplier')
            entry.supplier_name = supplier_from_je.get('supplier_name')
            entry.linked_purchase_invoice = supplier_from_je.get('purchase_invoice')
            entry.bill_no = supplier_from_je.get('bill_no')
    
    return entry

def get_supplier_from_journal_entry(journal_entry_name):
    """
    Get supplier information from Journal Entry by looking at the supplier control account entry.
    This is the most reliable method as you mentioned - the debited supplier control account
    holds the supplier name and purchase invoice reference.
    """
    try:
        # Query to find the supplier control account entry (usually debited)
        supplier_entry = frappe.db.sql("""
            SELECT 
                jea.party as supplier,
                jea.party_type,
                jea.reference_name as purchase_invoice,
                sup.supplier_name,
                pi.bill_no,
                jea.debit_in_account_currency,
                jea.account
            FROM `tabJournal Entry Account` jea
            LEFT JOIN `tabSupplier` sup ON jea.party = sup.name
            LEFT JOIN `tabPurchase Invoice` pi ON jea.reference_name = pi.name
            WHERE jea.parent = %s
            AND jea.party_type = 'Supplier'
            AND jea.debit_in_account_currency > 0
            ORDER BY jea.debit_in_account_currency DESC
            LIMIT 1
        """, (journal_entry_name,), as_dict=True)
        
        if supplier_entry:
            return {
                'supplier': supplier_entry[0].supplier,
                'supplier_name': supplier_entry[0].supplier_name,
                'purchase_invoice': supplier_entry[0].purchase_invoice,
                'bill_no': supplier_entry[0].bill_no
            }
        
        # Alternative: Look for any payable account entry
        payable_entry = frappe.db.sql("""
            SELECT 
                jea.party as supplier,
                jea.reference_name as purchase_invoice,
                sup.supplier_name,
                pi.bill_no
            FROM `tabJournal Entry Account` jea
            LEFT JOIN `tabSupplier` sup ON jea.party = sup.name
            LEFT JOIN `tabPurchase Invoice` pi ON jea.reference_name = pi.name
            WHERE jea.parent = %s
            AND jea.account_type = 'Payable'
            AND jea.party_type = 'Supplier'
            LIMIT 1
        """, (journal_entry_name,), as_dict=True)
        
        if payable_entry:
            return {
                'supplier': payable_entry[0].supplier,
                'supplier_name': payable_entry[0].supplier_name,
                'purchase_invoice': payable_entry[0].purchase_invoice,
                'bill_no': payable_entry[0].bill_no
            }
            
    except Exception as e:
        frappe.log_error(f"Error getting supplier from Journal Entry {journal_entry_name}: {str(e)}")
    
    return None

def is_tax_payment_entry(voucher_no, tax_account):
    """
    Check if a Journal Entry is a tax payment entry by analyzing its structure.
    Tax payment entries typically have:
    1. Debit to tax account (reducing liability)
    2. Credit to bank/cash account
    3. No supplier party involved
    """
    try:
        je_accounts = frappe.db.sql("""
            SELECT 
                account,
                debit_in_account_currency,
                credit_in_account_currency,
                party_type,
                party,
                account_type
            FROM `tabJournal Entry Account`
            WHERE parent = %s
        """, (voucher_no,), as_dict=True)
        
        if not je_accounts:
            return False
        
        # Check if this is a tax payment pattern
        has_tax_debit = False
        has_bank_credit = False
        has_supplier_party = False
        
        for account_entry in je_accounts:
            # Check for debit to tax account (payment reducing liability)
            if (account_entry.account == tax_account and 
                account_entry.debit_in_account_currency > 0):
                has_tax_debit = True
            
            # Check for credit to bank/cash account
            if (account_entry.account_type in ['Bank', 'Cash'] and 
                account_entry.credit_in_account_currency > 0):
                has_bank_credit = True
            
            # Check if there's a supplier party involved
            if account_entry.party_type == 'Supplier':
                has_supplier_party = True
        
        # If it has tax debit and bank credit but no supplier, it's likely a payment entry
        return has_tax_debit and has_bank_credit and not has_supplier_party
        
    except Exception as e:
        frappe.log_error(f"Error checking if tax payment entry: {str(e)}")
        return False

def get_voucher_tax_balance(voucher_no, tax_account):
    """Get the current balance for a specific voucher and tax account."""
    balance = frappe.db.sql("""
        SELECT SUM(debit - credit) as balance
        FROM `tabGL Entry`
        WHERE voucher_no = %s 
        AND account = %s 
        AND is_cancelled = 0
    """, (voucher_no, tax_account), as_dict=True)
    
    return balance[0].balance if balance and balance[0].balance is not None else 0

@frappe.whitelist()
def get_journal_entry_details(journal_entry_name):
    """
    Debug function to get detailed information about a Journal Entry.
    Useful for troubleshooting.
    """
    try:
        je_details = frappe.db.sql("""
            SELECT 
                je.name,
                je.posting_date,
                je.user_remark,
                jea.account,
                jea.party,
                jea.party_type,
                jea.reference_name,
                jea.debit_in_account_currency,
                jea.credit_in_account_currency,
                acc.account_type,
                sup.supplier_name,
                pi.bill_no
            FROM `tabJournal Entry` je
            JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
            LEFT JOIN `tabAccount` acc ON jea.account = acc.name
            LEFT JOIN `tabSupplier` sup ON jea.party = sup.name
            LEFT JOIN `tabPurchase Invoice` pi ON jea.reference_name = pi.name
            WHERE je.name = %s
            ORDER BY jea.idx
        """, (journal_entry_name,), as_dict=True)
        
        return je_details
        
    except Exception as e:
        frappe.log_error(f"Error getting Journal Entry details: {str(e)}")
        return []

@frappe.whitelist()
def validate_tax_payment_entries(doc):
    """Validate that selected entries are still available for payment"""
    if isinstance(doc, str):
        import json
        doc = json.loads(doc)
    
    selected_entries = [d for d in doc.get('tax_entries', []) if d.get('select_for_payment')]
    
    if not selected_entries:
        return {"valid": False, "message": "No entries selected for payment"}
    
    for entry in selected_entries:
        existing_payment = frappe.db.sql("""
            SELECT tp.name, tpe.payment_status
            FROM `tabTax Payment Entry` tpe
            INNER JOIN `tabTax Payment` tp ON tpe.parent = tp.name
            WHERE tpe.invoice = %s 
            AND tp.tax_account = %s
            AND tp.docstatus = 1
            AND tpe.payment_status = 'Paid'
            AND tp.name != %s
        """, (entry['invoice'], doc.get('tax_account'), doc.get('name', '')), as_dict=True)
        
        if existing_payment:
            return {
                "valid": False, 
                "message": f"Voucher {entry['invoice']} has already been paid in Tax Payment {existing_payment[0].name}"
            }
    
    return {"valid": True, "message": "All selected entries are valid for payment"}

@frappe.whitelist()
def create_tax_payment_journal_entry(tax_payment_doc, bank_account):
    """
    Create Journal Entry for tax payment to authorities.
    """
    if isinstance(tax_payment_doc, str):
        import json
        tax_payment_doc = json.loads(tax_payment_doc)
    
    try:
        total_amount = sum([flt(entry.get('tax_amount', 0)) 
                           for entry in tax_payment_doc.get('tax_entries', []) 
                           if entry.get('select_for_payment')])
        
        if total_amount <= 0:
            frappe.throw(_("No valid amount to process for tax payment"))
        
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = tax_payment_doc.get('company')
        je.posting_date = tax_payment_doc.get('payment_date', nowdate())
        je.user_remark = f"Tax payment to authorities for {tax_payment_doc.get('tax_account')}"
        
        je.append("accounts", {
            "account": tax_payment_doc.get('tax_account'),
            "debit_in_account_currency": total_amount,
            "credit_in_account_currency": 0
        })
        
        je.append("accounts", {
            "account": bank_account,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": total_amount
        })
        
        je.save()
        je.submit()
        
        return {
            "success": True,
            "journal_entry": je.name,
            "message": f"Journal Entry {je.name} created successfully for tax payment of {total_amount}"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating tax payment journal entry: {str(e)}")
        return {
            "success": False,
            "message": f"Error creating journal entry: {str(e)}"
        }
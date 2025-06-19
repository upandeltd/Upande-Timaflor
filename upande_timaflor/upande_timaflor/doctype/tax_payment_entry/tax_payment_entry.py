# tax_payment.py - DocType Controller

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, get_link_to_form

class TaxPayment(Document):
    def validate(self):
        self.validate_selected_entries()
        self.calculate_total_amount()
        self.validate_bank_account()
        
    def before_submit(self):
        self.validate_selected_entries()
        # Final validation before creating journal entry
        validation_result = self.validate_entries_availability()
        if not validation_result.get("valid"):
            frappe.throw(validation_result.get("message"))
    
    def on_submit(self):
        self.create_tax_payment_journal_entry()
        self.update_payment_status()
        
    def on_cancel(self):
        self.cancel_journal_entries()
        self.reset_payment_status()
    
    def validate_selected_entries(self):
        """Validate that at least one entry is selected for payment"""
        selected_entries = [d for d in self.tax_entries if d.select_for_payment]
        
        if not selected_entries and self.docstatus == 0:
            frappe.msgprint(_("Please select at least one tax entry for payment"))
            return
        elif not selected_entries and self.docstatus == 1:
            frappe.throw(_("No tax entries selected for payment"))
    
    def validate_entries_availability(self):
        """Check if selected entries are still available for payment"""
        selected_entries = [d for d in self.tax_entries if d.select_for_payment]
        
        for entry in selected_entries:
            # Check if this invoice has been paid in another Tax Payment document
            existing_payment = frappe.db.sql("""
                SELECT tp.name, tpe.payment_status
                FROM `tabTax Payment Entry` tpe
                INNER JOIN `tabTax Payment` tp ON tpe.parent = tp.name
                WHERE tpe.invoice = %s 
                AND tp.tax_account = %s
                AND tp.docstatus = 1
                AND tpe.payment_status = 'Paid'
                AND tp.name != %s
            """, (entry.invoice, self.tax_account, self.name), as_dict=True)
            
            if existing_payment:
                return {
                    "valid": False,
                    "message": _("Invoice {0} has already been paid in {1}").format(
                        entry.invoice, 
                        get_link_to_form("Tax Payment", existing_payment[0].name)
                    )
                }
        
        return {"valid": True}
    
    def calculate_total_amount(self):
        """Calculate total amount from selected entries"""
        total = 0
        for entry in self.tax_entries:
            if entry.select_for_payment:
                total += flt(entry.outstanding_amount)
        
        self.total_amount = total
    
    def validate_bank_account(self):
        """Validate that bank account is selected and is actually a bank account"""
        if not self.bank_account:
            frappe.throw(_("Bank Account is mandatory"))
        
        # Check if selected account is a bank account
        account_type = frappe.db.get_value("Account", self.bank_account, "account_type")
        if account_type != "Bank":
            frappe.throw(_("Selected account {0} is not a Bank account").format(self.bank_account))
    
    def create_tax_payment_journal_entry(self):
        """Create Journal Entry for the tax payment"""
        selected_entries = [d for d in self.tax_entries if d.select_for_payment]
        
        if not selected_entries:
            return
        
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Bank Entry"
        je.company = self.company
        je.posting_date = self.payment_date or nowdate()
        je.user_remark = f"Tax payment for {self.tax_account} via {self.name}"
        je.reference_type = "Tax Payment"
        je.reference_name = self.name
        
        total_amount = 0
        
        # Debit tax account (reduce liability/credit balance)
        for entry in selected_entries:
            je.append("accounts", {
                "account": self.tax_account,
                "debit_in_account_currency": flt(entry.outstanding_amount),
                "party_type": "Supplier",
                "party": entry.supplier,
                "reference_type": "Purchase Invoice",
                "reference_name": entry.invoice,
                "user_remark": f"Tax payment for invoice {entry.invoice} - {entry.bill_no}"
            })
            total_amount += flt(entry.outstanding_amount)
        
        # Credit bank account (cash outflow)
        je.append("accounts", {
            "account": self.bank_account,
            "credit_in_account_currency": total_amount,
            "user_remark": f"Tax payment via {self.name}"
        })
        
        try:
            je.insert()
            je.submit()
            
            # Update journal entry reference in tax payment entries
            for entry in selected_entries:
                entry.journal_entry = je.name
            
            frappe.msgprint(
                _("Journal Entry {0} created successfully").format(
                    get_link_to_form("Journal Entry", je.name)
                )
            )
            
        except Exception as e:
            frappe.throw(_("Error creating Journal Entry: {0}").format(str(e)))
    
    def update_payment_status(self):
        """Update payment status for selected entries"""
        for entry in self.tax_entries:
            if entry.select_for_payment:
                entry.payment_status = "Paid"
        
        self.save()
    
    def cancel_journal_entries(self):
        """Cancel associated journal entries"""
        journal_entries = list(set([d.journal_entry for d in self.tax_entries if d.journal_entry]))
        
        for je_name in journal_entries:
            if je_name:
                try:
                    je = frappe.get_doc("Journal Entry", je_name)
                    if je.docstatus == 1:
                        je.cancel()
                        frappe.msgprint(_("Journal Entry {0} cancelled").format(je_name))
                except Exception as e:
                    frappe.log_error(f"Error cancelling Journal Entry {je_name}: {str(e)}")
    
    def reset_payment_status(self):
        """Reset payment status for all entries"""
        for entry in self.tax_entries:
            entry.payment_status = "Pending"
            entry.journal_entry = None
        
        self.save()

# Hooks for other doctypes if needed
@frappe.whitelist()
def get_supplier_details(invoice):
    """Get supplier details for a given invoice"""
    return frappe.db.get_value("Purchase Invoice", invoice, 
                              ["supplier", "supplier_name", "bill_no"], as_dict=True)
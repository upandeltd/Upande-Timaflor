# custom_fields.py - Field configurations and filters

import frappe

def setup_custom_fields():
    """Setup custom fields and their configurations"""
    
    # Tax Payment Entry child table field configurations
    tax_payment_entry_fields = [
        {
            "fieldname": "invoice",
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "label": "Invoice",
            "reqd": 1,
            "read_only": 1,
            "in_list_view": 1,
            "width": "120px"
        },
        {
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "label": "Supplier",
            "read_only": 1,
            "in_list_view": 1,
            "width": "150px"
        },
        {
            "fieldname": "bill_no",
            "fieldtype": "Data",
            "label": "Bill No",
            "read_only": 1,
            "in_list_view": 1,
            "width": "100px"
        },
        {
            "fieldname": "tax_amount",
            "fieldtype": "Currency",
            "label": "Tax Amount",
            "read_only": 1,
            "in_list_view": 1,
            "width": "100px"
        },
        {
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "label": "Outstanding Amount",
            "read_only": 1,
            "in_list_view": 1,
            "width": "120px"
        },
        {
            "fieldname": "select_for_payment",
            "fieldtype": "Check",
            "label": "Select for Payment",
            "in_list_view": 1,
            "width": "80px"
        },
        {
            "fieldname": "payment_status",
            "fieldtype": "Select",
            "options": "Pending\nPaid",
            "default": "Pending",
            "label": "Payment Status",
            "read_only": 1,
            "in_list_view": 1,
            "width": "100px"
        },
        {
            "fieldname": "journal_entry",
            "fieldtype": "Link",
            "options": "Journal Entry",
            "label": "Journal Entry",
            "read_only": 1,
            "width": "120px"
        }
    ]

# Account filters for Tax Payment doctype
TAX_ACCOUNT_FILTER = """
function(doc) {
    return {
        filters: {
            "company": doc.company,
            "account_type": "Tax",
            "is_group": 0
        }
    }
}
"""

BANK_ACCOUNT_FILTER = """
function(doc) {
    return {
        filters: {
            "company": doc.company,
            "account_type": "Bank",
            "is_group": 0
        }
    }
}
"""

# Server Script for Tax Payment Entry child table
TAX_PAYMENT_ENTRY_SERVER_SCRIPT = """
# Server Script for Tax Payment Entry
# This script auto-populates supplier and bill_no when invoice is selected

if frappe.form_dict.get("cmd") == "frappe.desk.form.load.getdoc":
    pass
else:
    # This runs when a field is changed
    if doc.invoice and not doc.supplier:
        invoice_details = frappe.db.get_value("Purchase Invoice", doc.invoice, 
                                            ["supplier", "bill_no"], as_dict=True)
        if invoice_details:
            doc.supplier = invoice_details.supplier
            doc.bill_no = invoice_details.bill_no
"""

# Property Setter configurations
PROPERTY_SETTERS = [
    {
        "doctype": "Tax Payment",
        "field": "tax_account",
        "property": "options",
        "value": TAX_ACCOUNT_FILTER
    },
    {
        "doctype": "Tax Payment", 
        "field": "bank_account",
        "property": "options",
        "value": BANK_ACCOUNT_FILTER
    }
]

def create_custom_fields():
    """Create custom fields programmatically"""
    
    # This would be used in a migration or setup script
    for field in tax_payment_entry_fields:
        if not frappe.db.exists("Custom Field", {
            "dt": "Tax Payment Entry",
            "fieldname": field["fieldname"]
        }):
            custom_field = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Tax Payment Entry",
                **field
            })
            custom_field.insert()

def setup_property_setters():
    """Setup property setters for filters"""
    
    for ps in PROPERTY_SETTERS:
        if not frappe.db.exists("Property Setter", {
            "doc_type": ps["doctype"],
            "field_name": ps["field"],
            "property": ps["property"]
        }):
            property_setter = frappe.get_doc({
                "doctype": "Property Setter",
                "doc_type": ps["doctype"],
                "field_name": ps["field"],
                "property": ps["property"],
                "value": ps["value"]
            })
            property_setter.insert()
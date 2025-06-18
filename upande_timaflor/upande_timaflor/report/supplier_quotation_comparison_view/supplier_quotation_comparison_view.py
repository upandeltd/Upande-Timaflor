import frappe # type: ignore
import json
from frappe.utils import nowdate # type: ignore
from frappe import _ # type: ignore

def execute(filters=None):
    """
    Executes the RFQ Comparison report.
    """
    if not filters or not filters.get("rfq"):
        frappe.msgprint(_("Please select an RFQ to generate the report."), title=_("Missing RFQ"))
        return [], []

    rfq_name = filters["rfq"]
    
    # Get company's default currency for display purposes
    company_currency = frappe.get_value("Company", frappe.defaults.get_user_default("Company"), "default_currency")
    if not company_currency:
        frappe.msgprint(_("Default company currency not found. Please set it up."), title=_("Configuration Error"))
        return [], []

<<<<<<< HEAD
    rfq_items = get_rfq_items(rfq_name)
    if not rfq_items:
        frappe.msgprint(_("No items found in the selected Request for Quotation."), title=_("No Items"))
        return [], []

    supplier_list = get_rfq_suppliers(rfq_name)
    if not supplier_list:
        frappe.msgprint(_("No suppliers linked to the selected Request for Quotation."), title=_("No Suppliers"))
        return [], []

    supplier_quotes = get_supplier_quotes(supplier_list, rfq_name)
    if not supplier_quotes:
        frappe.msgprint(_("No submitted supplier quotations found for the linked suppliers and RFQ items."), title=_("No Quotations"))
        return [], []

    columns, data = build_table_data(rfq_items, supplier_quotes, company_currency, rfq_name)
    
    return columns, data

def get_rfq_items(rfq_name):
    """
    Fetches distinct items from the Request for Quotation.
    """
    return frappe.get_all(
=======
    # Get all items from the RFQ
    rfq_items = frappe.get_all(
>>>>>>> fa59d8d972870820c1d43b32b7cc02d49dc573ac
        "Request for Quotation Item",
        filters={"parent": rfq_name},
        fields=["item_code", "item_name", "uom"],
        distinct=True
    )

<<<<<<< HEAD
def get_rfq_suppliers(rfq_name):
    """
    Fetches all suppliers linked to the Request for Quotation.
    """
    rfq_suppliers = frappe.get_all(
        "Request for Quotation Supplier",
        filters={"parent": rfq_name},
        fields=["supplier"]
    )
    return [d.supplier for d in rfq_suppliers]

def get_supplier_quotes(supplier_list, rfq_name):
    """
    Fetches submitted supplier quotation items related to the RFQ's suppliers and items.
    """
    return frappe.db.sql("""
        SELECT

            sq.name AS quotation_name,
=======
    # Get Supplier Quotations linked to the RFQ
    supplier_quotes = frappe.db.sql("""
        SELECT 
>>>>>>> fa59d8d972870820c1d43b32b7cc02d49dc573ac
            sq.supplier,
            sqi.item_code,
            sqi.item_name,
            sqi.uom,
            sqi.qty,
            sqi.rate
<<<<<<< HEAD
        FROM `tabSupplier Quotation` sq
        INNER JOIN `tabSupplier Quotation Item` sqi ON sq.name = sqi.parent
        WHERE sq.docstatus = 1 -- Only consider submitted quotations
          AND sq.supplier IN %(suppliers)s
          AND sqi.item_code IN (
              SELECT item_code FROM `tabRequest for Quotation Item` WHERE parent = %(rfq)s
          )
    """, {"suppliers": tuple(supplier_list), "rfq": rfq_name}, as_dict=True)

def build_table_data(rfq_items, supplier_quotes, company_currency, rfq_name):
    """
    Builds the columns and data for the report table.
    """
    supplier_meta = {}
    for quote in supplier_quotes:
        supplier = quote["supplier"]
        if supplier not in supplier_meta:
            supplier_meta[supplier] = {
                "currency": quote.get("currency") or company_currency,
                "quotation_name": quote["quotation_name"]
            }

    suppliers = sorted(supplier_meta.keys())

    columns = [
        {"label": _("QTY"), "fieldname": "rfq_qty", "fieldtype": "Float", "width": 80},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 80},
        {"label": _("ITEM CODE"), "fieldname": "item_code", "fieldtype": "Data", "width": 120},
        {"label": _("ITEM NAME"), "fieldname": "item_name", "fieldtype": "Data", "width": 260}
        
        
    ]

    for supplier in suppliers:
        quotation_name = supplier_meta[supplier]["quotation_name"]
        link = f"/app/supplier-quotation/{quotation_name}"
        columns.append({
            "label": f'<a href="{link}" style="text-decoration:none;" target="_blank">{supplier}</a>',
            "fieldname": supplier,
            "fieldtype": "HTML",
            "width": 300
        })

    rate_map = {}
    for q in supplier_quotes:
        key = (q.item_code, q.supplier)
        rate_map[key] = {
            "rate": q.rate,
            "currency": q.get("currency") or company_currency,
            "quotation_name": q.quotation_name,
            "item_name": q.item_name,
            "uom": q.uom,
            "qty": q.qty
        }

=======
        FROM 
            `tabSupplier Quotation` sq
        INNER JOIN 
            `tabSupplier Quotation Item` sqi ON sq.name = sqi.parent
        WHERE 
            request_for_quotation = %s
        ORDER BY 
            sq.supplier
    """, rfq_name, as_dict=True)

    if not supplier_quotes:
        frappe.msgprint("No supplier quotations found.")
        return [], []

    # Determine unique supplier list
    suppliers = sorted(list({q["supplier"] for q in supplier_quotes}))
    supplier_columns = [{"label": s, "fieldname": s, "fieldtype": "Currency"} for s in suppliers]

    # Define columns
    columns = [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
    ] + supplier_columns

    # Map of (item_code, supplier) -> rate
    rate_map = {(q["item_code"], q["supplier"]): q["rate"] for q in supplier_quotes}

    # Build rows
>>>>>>> fa59d8d972870820c1d43b32b7cc02d49dc573ac
    data = []
    rfq_item_qty_map = {item.item_code: frappe.get_value("Request for Quotation Item", {"parent": rfq_name, "item_code": item.item_code}, "qty") for item in rfq_items}


    for item in rfq_items:
        row = {
            "item_code": item.item_code,
<<<<<<< HEAD
            "item_name": item.item_name,
            "uom": item.uom,
            "rfq_qty": rfq_item_qty_map.get(item.item_code, 0)
        }

        item_rates_for_comparison = {}
        for sup in suppliers:
            meta = rate_map.get((item.item_code, sup))
            if meta and meta["rate"] is not None:
                item_rates_for_comparison[sup] = meta["rate"]

        valid_rates = list(item_rates_for_comparison.values())
        min_rate = min(valid_rates) if valid_rates else None
        max_rate = max(valid_rates) if valid_rates else None

        for sup in suppliers:
            meta = rate_map.get((item.item_code, sup))
            if not meta:
                row[sup] = ""
                continue

            rate = meta["rate"]
            currency = meta["currency"]
            item_name = meta["item_name"]
            uom = meta["uom"]
            qty = meta["qty"]

            color = "black"
            if rate is not None:
                if min_rate is not None and rate == min_rate:
                    color = "green"
                elif max_rate is not None and rate == max_rate:
                    color = "red"

            money_formatted = frappe.utils.fmt_money(rate, precision=2, currency=currency) if rate is not None else _("N/A")

            checkbox = (
                f'<input type="checkbox" class="sq-select" '
                f'data-item="{item.item_code}" data-item-name="{item_name}" data-uom="{uom}" '
                f'data-qty="{qty}" data-rate="{rate}" data-supplier="{sup}" '
                f'data-currency="{currency}" style="margin-right:4px;">'
            )

            row[sup] = f'{checkbox}<span style="color:{color};">{money_formatted}</span>'

=======
            "item_name": item.item_name
        }
        for supplier in suppliers:
            row[supplier] = rate_map.get((item.item_code, supplier), None)
>>>>>>> fa59d8d972870820c1d43b32b7cc02d49dc573ac
        data.append(row)

    return columns, data

def check_for_duplicate_po(supplier, items_to_check):
    """
    Checks if a Purchase Order with the same supplier and exact items (item_code, qty, rate) already exists.
    items_to_check: List of dictionaries with 'item_code', 'qty', 'rate'
    """
    # Create a canonical representation of the items to check for comparison
    # Sort by item_code for consistent comparison
    current_po_items_canonical = sorted([
        (item['item_code'], float(item['qty']), float(item['rate']))
        for item in items_to_check
    ])

    # Get all submitted Purchase Orders for the given supplier
    existing_pos = frappe.get_all(
        "Purchase Order",
        filters={"supplier": supplier, "docstatus": 1}, # Only submitted POs
        fields=["name"]
    )

    for po_doc_name in existing_pos:
        po_name = po_doc_name.name
        
        # Get items for the existing Purchase Order
        existing_po_items = frappe.get_all(
            "Purchase Order Item",
            filters={"parent": po_name},
            fields=["item_code", "qty", "rate"]
        )

        # Create a canonical representation of the existing PO's items
        existing_po_items_canonical = sorted([
            (item.item_code, float(item.qty), float(item.rate))
            for item in existing_po_items
        ])

        # Compare the two canonical lists
        if current_po_items_canonical == existing_po_items_canonical:
            return po_name # Found a duplicate, return its name

    return None # No duplicate found

@frappe.whitelist()
def create_purchase_orders_from_rfq(selections):
    """
    Creates Purchase Orders from selected supplier quotation items.
    Prevents creation of duplicate Purchase Orders.
    """
    try:
        selections = json.loads(selections)
    except json.JSONDecodeError:
        frappe.throw(_("Invalid selections data received."))

    if not selections:
        frappe.throw(_("No items selected for Purchase Order creation."))

    supplier_map = {}
    for s in selections:
        key = s["supplier"]
        supplier_map.setdefault(key, []).append(s)

    created_po_names = []
    errors = []
    
    # Get the default company only once
    default_company = frappe.defaults.get_user_default("Company")
    if not default_company:
        frappe.throw(_("Default Company not found. Please set it up in User Defaults."), title=_("Configuration Error"))

    for supplier, items in supplier_map.items():
        # --- Check for duplicate PO before creating ---
        duplicate_po_name = check_for_duplicate_po(supplier, items)
        if duplicate_po_name:
            errors.append(_("Purchase Order for supplier {0} with these items already exists: {1}").format(supplier, duplicate_po_name))
            continue # Skip creating this PO

        try:
            po = frappe.new_doc("Purchase Order")
            po.supplier = supplier
            
            # --- MANDATORY FIELD: company ---
            po.company = default_company 
            
            # Use currency from first item, fallback to company default
            po.currency = items[0].get("currency", frappe.get_value("Company", default_company, "default_currency"))
            
            po.transaction_date = nowdate()
            po.schedule_date = nowdate()

            for item in items:
                po_item = {
                    "item_code": item["item_code"],
                    "item_name": item.get("item_name"),
                    "uom": item.get("uom"),
                    "qty": float(item.get("qty", 1)),
                    "rate": float(item.get("rate", 0)),
                    "schedule_date": nowdate(),
                    # --- MANDATORY FIELD: uom_conversion_factor ---
                    "uom_conversion_factor": 1.0, 
                    # "warehouse": "Your Default Warehouse" # Uncomment and set if mandatory in your setup
                }
                # Example for warehouse if mandatory:
                # po_item["warehouse"] = frappe.get_value("Company", default_company, "default_warehouse")

                po.append("items", po_item)
            
            po.insert(ignore_permissions=True)
            po.submit()
            created_po_names.append(po.name)
            
        except Exception as e:
            frappe.logger("rfq_comparison_report").error(f"Error creating PO for supplier {supplier}: {frappe.utils.get_traceback()}")
            errors.append(_("Failed to create PO for {0}: {1}").format(supplier, str(e)))

    if errors:
        error_message = _("Some Purchase Orders could not be created/skipped due to duplicates:") + "\n" + "\n".join(errors)
        frappe.throw(error_message, title=_("PO Creation Status"))
    else:
        return {"purchase_orders": created_po_names, "message": _("Purchase Orders created successfully.")}


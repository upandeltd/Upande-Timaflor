# Copyright (c) 2025, newton@upande.com and contributors
import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe import _
import json

class OrderingSheet(Document):
    @frappe.whitelist()
    def create_purchase_order(self, supplier=None):
        """Create Purchase Order from Ordering Sheet"""
        if not self.order_quantity:
            frappe.throw(_("No order quantities available - please calculate order quantities first"))

        final_supplier = supplier or self.supplier
        if not final_supplier:
            frappe.throw(_("Supplier must be selected during PO creation"))

        po = frappe.new_doc("Purchase Order")
        po.supplier = final_supplier
        po.company = frappe.defaults.get_user_default("Company")
        
        for order_item in self.order_quantity:
            total_qty = sum([
                order_item.tima_1 or 0,
                order_item.tima_2 or 0,
                order_item.tima_3 or 0,
                order_item.tima_4 or 0,
                order_item.tima_5 or 0,
                order_item.tima_6 or 0,
                order_item.tima_7 or 0,
                order_item.jangwani or 0  
            ])

            if total_qty > 0:
                # Get item details including stock_uom
                item_details = frappe.db.get_value("Item", order_item.item, 
                    ["item_name", "description", "stock_uom"], as_dict=1)
                
                po.append("items", {
                    "item_code": order_item.item,
                    "qty": total_qty,
                    "schedule_date": frappe.utils.nowdate(),
                    "conversion_factor": 1.0,  
                    "uom": item_details.stock_uom if item_details else "Nos",
                    "stock_uom": item_details.stock_uom if item_details else "Nos"
                })

        if not po.get("items"):
            frappe.throw(_("No items with positive quantities found"))

        po.insert(ignore_permissions=True)
        po.submit()
        frappe.db.commit()
        return po.name
        
    @frappe.whitelist()
    def calculate_order_quantities(self, calculation_base, ordering_quantity):
        """Calculate order quantities based on consumption data"""
        if not calculation_base or not ordering_quantity:
            frappe.throw(_("Calculation base and ordering quantity are required"))
            
        # Clear current order quantities
        self.order_quantity = []
        
        # Get source data based on calculation base
        source_table = None
        field_map = {}
        
        if calculation_base == 'Average Consumption':
            source_table = self.table_bvnr
            field_map = {
                't1_avg': 'tima_1',
                't2_avg': 'tima_2',
                't3_avg': 'tima_3',
                't4_avg': 'tima_4',
                't5_avg': 'tima_5',
                't6_avg': 'tima_6',
                't7_avg': 'tima_7',
                'jangwani_avg': 'jangwani'
            }
        elif calculation_base == 'Minimum Consumption':
            source_table = self.daily_minimum_consumption
            field_map = {
                'tima_1_minimum': 'tima_1',
                'tima_2_minimum': 'tima_2',
                'tima_3_minimum': 'tima_3',
                'tima_4_minimum': 'tima_4',
                'tima_5_minimum': 'tima_5',
                'tima_6_minimum': 'tima_6',
                'tima_7_minimum': 'tima_7',
                'jangwani_minimum': 'jangwani'
            }
        elif calculation_base == 'Maximum Consumption':
            source_table = self.daily_maximum_consumption
            field_map = {
                'tima_1_daily_avg': 'tima_1',
                'tima_2_daily_avg': 'tima_2',
                'tima_3_daily_avg': 'tima_3',
                'tima_4_daily_avg': 'tima_4',
                'tima_5_daily_avg': 'tima_5',
                'tima_6_daily_avg': 'tima_6',
                'tima_7_daily_avg': 'tima_7',
                'jangwani_daily_avg': 'jangwani'
            }
        else:
            frappe.throw(_("Invalid calculation base selected"))
        
        # Calculate new order quantities
        if source_table and len(source_table) > 0:
            ordering_qty = float(ordering_quantity)
            
            for source_row in source_table:
                order_row = self.append("order_quantity", {})
                order_row.item = source_row.item
                
                for source_field, target_field in field_map.items():
                    base_value = float(source_row.get(source_field) or 0)
                    calculated_value = base_value * ordering_qty
                    order_row.set(target_field, calculated_value)
                    
        # Save but don't submit
        self.save()
        return self.name

@frappe.whitelist()
def get_average_consumption(item_code, from_date, to_date):
    """Calculate average daily consumption per farm"""
    from_date = datetime.strptime(from_date, "%Y-%m-%d")
    to_date = datetime.strptime(to_date, "%Y-%m-%d")

    days = (to_date - from_date).days
    if days <= 0: return {}

    stock_movement = frappe.db.sql("""
        SELECT 
            w.farm AS farm,
            SUM(sle.actual_qty) AS total_qty
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
        WHERE 
            sle.item_code = %s 
            AND sle.posting_date BETWEEN %s AND %s
            AND w.farm IS NOT NULL
        GROUP BY w.farm
    """, (item_code, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")), as_dict=True)

    return {entry.farm: (entry.total_qty or 0)/days for entry in stock_movement if days}

@frappe.whitelist()
def get_all_consumption_data(item_codes, from_date, to_date):
    try:
        if isinstance(item_codes, str):
            item_codes = json.loads(item_codes)
        
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
        days = (to_date_obj - from_date_obj).days
        
        if days <= 0: 
            return {"average": {}, "minimum": {}, "maximum": {}}
        
        result = {"average": {}, "minimum": {}, "maximum": {}}
        
        for item_code in item_codes:
            result["average"][item_code] = {}
            result["minimum"][item_code] = {}
            result["maximum"][item_code] = {}
            
            stock_data = frappe.db.sql("""
                SELECT 
                    w.farm AS farm,
                    DATE(sle.posting_date) AS posting_date,
                    SUM(sle.actual_qty) AS daily_qty
                FROM `tabStock Ledger Entry` sle
                LEFT JOIN `tabWarehouse` w ON sle.warehouse = w.name
                WHERE 
                    sle.item_code = %s 
                    AND sle.posting_date BETWEEN %s AND %s
                    AND w.farm IS NOT NULL
                GROUP BY w.farm, DATE(sle.posting_date)
            """, (item_code, from_date, to_date), as_dict=True)
            
            farm_daily_data = {}
            for entry in stock_data:
                farm = entry.farm
                if farm not in farm_daily_data:
                    farm_daily_data[farm] = []
                if entry.daily_qty is not None:
                    farm_daily_data[farm].append(float(entry.daily_qty))
            
            for farm, daily_values in farm_daily_data.items():
                if daily_values:
                    result["average"][item_code][farm] = sum(daily_values) / len(daily_values)
                    result["minimum"][item_code][farm] = min(daily_values)
                    result["maximum"][item_code][farm] = max(daily_values)
                else:
                    result["average"][item_code][farm] = 0
                    result["minimum"][item_code][farm] = 0
                    result["maximum"][item_code][farm] = 0
            
            all_farms = ["Tima1", "Tima2", "Tima3", "Tima4", "Tima5", "Tima6", "Tima7", "Jangwani"]
            for farm in all_farms:
                if farm not in farm_daily_data:
                    result["average"][item_code][farm] = 0
                    result["minimum"][item_code][farm] = 0
                    result["maximum"][item_code][farm] = 0
        
        return result
    except Exception as e:
        frappe.log_error(f"Error in get_all_consumption_data: {str(e)}", "Consumption Data Error")
        raise

@frappe.whitelist()
def create_rfq(ordering_sheet):
    """Create RFQ without suppliers/message"""
    if not ordering_sheet:
        frappe.throw(_("Ordering Sheet is required"))
    
    doc = frappe.get_doc("Ordering Sheet", ordering_sheet)
    
    if not doc.order_quantity or len(doc.order_quantity) == 0:
        frappe.throw(_("No order quantities found - please calculate order quantities first"))
    
    rfq = frappe.new_doc("Request for Quotation")
    
    # Bypass mandatory field validation during insert
    rfq.flags.ignore_mandatory = True
    
    rfq.transaction_date = frappe.utils.nowdate()
    rfq.company = frappe.defaults.get_user_default("Company")
    rfq.ordering_sheet = ordering_sheet
    
    # Add items 
    for order_item in doc.order_quantity:
        total_qty = sum([
            order_item.tima_1 or 0,
            order_item.tima_2 or 0,
            order_item.tima_3 or 0,
            order_item.tima_4 or 0,
            order_item.tima_5 or 0,
            order_item.tima_6 or 0,
            order_item.tima_7 or 0,
            order_item.jangwani or 0  
        ])
        
        if total_qty > 0:
            item_details = frappe.db.get_value("Item", order_item.item, 
                ["item_name", "description", "stock_uom"], as_dict=1)
            
            rfq.append("items", {
                "item_code": order_item.item,
                "qty": total_qty,
                "item_name": item_details.item_name if item_details else "",
                "description": item_details.description if item_details else "",
                "uom": item_details.stock_uom if item_details else "Nos",
                "conversion_factor": 1.0,  # Added mandatory conversion_factor
                "stock_uom": item_details.stock_uom if item_details else "Nos",  # Added stock_uom
                "warehouse": frappe.db.get_single_value("Stock Settings", "default_warehouse") or ""
            })
    
    # Insert as draft without validations
    rfq.insert(ignore_permissions=True, ignore_mandatory=True)
    
    # Add a note in the document about missing suppliers
    rfq.add_comment('Comment', 'Created without suppliers - please add suppliers before submitting')
    
    frappe.db.commit()
    return rfq.name

@frappe.whitelist()
def get_items_for_rfq(ordering_sheet):
    if not ordering_sheet:
        frappe.throw(_("Ordering Sheet is required"))
    
    doc = frappe.get_doc("Ordering Sheet", ordering_sheet)
    if not doc.order_quantity or len(doc.order_quantity) == 0:
        frappe.throw(_("No order quantities found - please calculate order quantities first"))
    
    items = []
    for order_item in doc.order_quantity:
        total_qty = sum([
            order_item.tima_1 or 0,
            order_item.tima_2 or 0,
            order_item.tima_3 or 0,
            order_item.tima_4 or 0,
            order_item.tima_5 or 0,
            order_item.tima_6 or 0,
            order_item.tima_7 or 0,
            order_item.jangwani or 0  
        ])
        
        if total_qty > 0:
            item_details = frappe.db.get_value("Item", order_item.item, 
                ["item_name", "description", "stock_uom"], as_dict=1)
            
            items.append({
                "item": order_item.item,
                "total_qty": total_qty,
                "item_name": item_details.item_name if item_details else "",
                "description": item_details.description if item_details else "",
                "uom": item_details.stock_uom if item_details else "Nos"
            })
    
    return items

# New methods to handle calculations for submitted documents
@frappe.whitelist()
def update_order_quantities(doc_name, calculation_base, ordering_quantity):
    """Update order quantities for a submitted document"""
    if not doc_name:
        frappe.throw(_("Document name is required"))
        
    doc = frappe.get_doc("Ordering Sheet", doc_name)
    
    if doc.docstatus != 1:
        frappe.throw(_("Document must be submitted to update via this method"))
    
    # Use workflow that preserves submitted state
    # Store original values
    old_amended_from = doc.amended_from
    old_docstatus = doc.docstatus
    
    # Clear order quantities
    doc.order_quantity = []
    
    # Get source data based on calculation base
    source_table = None
    field_map = {}
    
    if calculation_base == 'Average Consumption':
        source_table = doc.table_bvnr
        field_map = {
            't1_avg': 'tima_1',
            't2_avg': 'tima_2',
            't3_avg': 'tima_3',
            't4_avg': 'tima_4',
            't5_avg': 'tima_5',
            't6_avg': 'tima_6',
            't7_avg': 'tima_7',
            'jangwani_avg': 'jangwani'
        }
    elif calculation_base == 'Minimum Consumption':
        source_table = doc.daily_minimum_consumption
        field_map = {
            'tima_1_minimum': 'tima_1',
            'tima_2_minimum': 'tima_2',
            'tima_3_minimum': 'tima_3',
            'tima_4_minimum': 'tima_4',
            'tima_5_minimum': 'tima_5',
            'tima_6_minimum': 'tima_6',
            'tima_7_minimum': 'tima_7',
            'jangwani_minimum': 'jangwani'
        }
    elif calculation_base == 'Maximum Consumption':
        source_table = doc.daily_maximum_consumption
        field_map = {
            'tima_1_daily_avg': 'tima_1',
            'tima_2_daily_avg': 'tima_2',
            'tima_3_daily_avg': 'tima_3',
            'tima_4_daily_avg': 'tima_4',
            'tima_5_daily_avg': 'tima_5',
            'tima_6_daily_avg': 'tima_6',
            'tima_7_daily_avg': 'tima_7',
            'jangwani_daily_avg': 'jangwani'
        }
    else:
        frappe.throw(_("Invalid calculation base selected"))
    
    # Calculate new order quantities
    if source_table and len(source_table) > 0:
        ordering_qty = float(ordering_quantity)
        
        for source_row in source_table:
            order_row = doc.append("order_quantity", {})
            order_row.item = source_row.item
            
            for source_field, target_field in field_map.items():
                base_value = float(source_row.get(source_field) or 0)
                calculated_value = base_value * ordering_qty
                order_row.set(target_field, calculated_value)
    
    # Use direct DB updates to maintain submitted state
    frappe.db.set_value("Ordering Sheet", doc_name, {
        "amended_from": old_amended_from,
        "docstatus": old_docstatus
    })
    
    # Update the child table data
    if doc.order_quantity:
        # Delete existing order quantity items
        frappe.db.sql("""
            DELETE FROM `tabOrdering Sheet Item`
            WHERE parent = %s
        """, (doc_name,))
        
        # Insert new order quantity items
        for i, item in enumerate(doc.order_quantity):
            item.parent = doc_name
            item.parenttype = "Ordering Sheet"
            item.parentfield = "order_quantity"
            item.idx = i + 1
            item.insert()
    
    frappe.db.commit()
    return doc_name

@frappe.whitelist()
def add_custom_order_quantity(doc_name, item_values):
    """Add custom order quantity to a submitted document"""
    if not doc_name:
        frappe.throw(_("Document name is required"))
    
    if isinstance(item_values, str):
        item_values = json.loads(item_values)
    
    doc = frappe.get_doc("Ordering Sheet", doc_name)
    
    if doc.docstatus != 1:
        frappe.throw(_("Document must be submitted to update via this method"))
    
    # Use direct DB approach to maintain submitted state
    # First get current order_quantity items
    current_items = frappe.get_all("Ordering Sheet Item", 
        filters={"parent": doc_name, "parentfield": "order_quantity"},
        fields=["*"], order_by="idx")
    
    # Create new item
    new_item = frappe.new_doc("Ordering Sheet Item")
    new_item.parent = doc_name
    new_item.parenttype = "Ordering Sheet"
    new_item.parentfield = "order_quantity"
    new_item.idx = len(current_items) + 1
    new_item.item = item_values.get('item')
    new_item.tima_1 = float(item_values.get('tima_1') or 0)
    new_item.tima_2 = float(item_values.get('tima_2') or 0)
    new_item.tima_3 = float(item_values.get('tima_3') or 0)
    new_item.tima_4 = float(item_values.get('tima_4') or 0)
    new_item.tima_5 = float(item_values.get('tima_5') or 0)
    new_item.tima_6 = float(item_values.get('tima_6') or 0)
    new_item.tima_7 = float(item_values.get('tima_7') or 0)
    new_item.jangwani = float(item_values.get('jangwani') or 0)
    new_item.insert()
    
    frappe.db.commit()
    return doc_name
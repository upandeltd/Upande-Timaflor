# Copyright (c) 2025, newton@upande.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta


class FertilizerOrderSheet(Document):
    pass


@frappe.whitelist()
def calculate_fertilizer_matrix_data(average_consumption, stock_wantedweeks):
    """
    Calculate average consumption, current stock levels, and order quantities for all fertilizer items
    organized in a matrix format with farms as columns.
    
    Args:
        average_consumption (int): Number of weeks to consider for average calculation
        stock_wantedweeks (int): Number of weeks being ordered for
    
    Returns:
        dict: Contains lists of average consumption, stock levels, and calculated order quantities
    """
    # Convert string inputs to integers
    avg_consumption_weeks = int(average_consumption)
    wanted_weeks = int(stock_wantedweeks)
    
    # Get all fertilizer items
    fertilizer_items = get_fertilizer_items()
    
    farms = ["Tima1", "Tima2", "Tima3", "Tima4", "Tima5", "Tima6", "Tima7", "Jangwani"]
    
    # Get farm warehouses mapping
    farm_warehouses = {}
    for farm in farms:
        farm_warehouses[farm] = get_farm_warehouses(farm)
    
    consumption_data = calculate_average_consumption_matrix(fertilizer_items, farm_warehouses, avg_consumption_weeks)
    
    stock_data = get_current_stock_levels_matrix(fertilizer_items, farm_warehouses)
    
    order_qty_data = calculate_order_quantities_matrix(consumption_data, stock_data, wanted_weeks)
    
    return {
        "consumption": consumption_data,
        "stock": stock_data,
        "order_qty": order_qty_data
    }


def get_fertilizer_items():
    """Get all items from the Fertilizer Item Group"""
    items = frappe.get_all(
        "Item",
        filters={"item_group": "Fertilizer"},
        fields=["name as item_code", "item_name", "stock_uom as uom"]
    )
    return items


def get_farm_warehouses(farm):
    """Get all warehouses linked to the specified farm"""
    warehouses = frappe.get_all(
        "Warehouse",
        filters={"farm": farm},
        fields=["name"]
    )
    return [w.name for w in warehouses]


def calculate_average_consumption_matrix(fertilizer_items, farm_warehouses, weeks):
    """
    Calculate average weekly consumption for each fertilizer item
    for each farm based on the specified number of weeks
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks)
    
    consumption_data = []
    
    for item in fertilizer_items:
        item_data = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "uom": item.uom,
            "tima_1": 0,
            "tima_2": 0,
            "tima_3": 0,
            "tima_4": 0,
            "tima_5": 0,
            "tima_6": 0,
            "tima_7": 0,
            "jangwani": 0
        }
        
        # Calculate consumption for each farm
        farm_mapping = {
            "Tima1": "tima_1",
            "Tima2": "tima_2",
            "Tima3": "tima_3",
            "Tima4": "tima_4",
            "Tima5": "tima_5",
            "Tima6": "tima_6",
            "Tima7": "tima_7",
            "Jangwani": "jangwani"
        }
        
        for farm, warehouses in farm_warehouses.items():
            if not warehouses:
                continue
                
            # Query stock ledger entries to calculate consumption for farm warehouses
            consumption = frappe.db.sql("""
                SELECT SUM(actual_qty) * -1 as total_consumption
                FROM `tabStock Ledger Entry`
                WHERE item_code = %s
                AND warehouse IN %s
                AND posting_date BETWEEN %s AND %s
                AND actual_qty < 0
            """, (item.item_code, warehouses, start_date, end_date), as_dict=1)
            
            total_consumption = consumption[0].total_consumption if consumption[0].total_consumption else 0
            avg_consumption = total_consumption / weeks if total_consumption else 0
            
            # Map farm to the corresponding field name
            field_name = farm_mapping.get(farm, "").lower()
            if field_name:
                item_data[field_name] = avg_consumption
        
        consumption_data.append(item_data)
    
    return consumption_data


def get_current_stock_levels_matrix(fertilizer_items, farm_warehouses):
    """Get current stock levels for all fertilizer items for each farm"""
    stock_data = []
    
    for item in fertilizer_items:
        item_data = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "uom": item.uom,
            "tima_1": 0,
            "tima_2": 0,
            "tima_3": 0,
            "tima_4": 0,
            "tima_5": 0,
            "tima_6": 0,
            "tima_7": 0,
            "jangwani": 0
        }
        
        # Calculate stock for each farm
        farm_mapping = {
            "Tima1": "tima_1",
            "Tima2": "tima_2",
            "Tima3": "tima_3",
            "Tima4": "tima_4",
            "Tima5": "tima_5",
            "Tima6": "tima_6",
            "Tima7": "tima_7",
            "Jangwani": "jangwani"
        }
        
        for farm, warehouses in farm_warehouses.items():
            if not warehouses:
                continue
                
            # Get current stock balance from Bin
            stock_balance = frappe.db.sql("""
                SELECT SUM(actual_qty) as current_stock
                FROM `tabBin`
                WHERE item_code = %s
                AND warehouse IN %s
            """, (item.item_code, warehouses), as_dict=1)
            
            current_stock = stock_balance[0].current_stock if stock_balance[0].current_stock else 0
            
            field_name = farm_mapping.get(farm, "").lower()
            if field_name:
                item_data[field_name] = current_stock
        
        stock_data.append(item_data)
    
    return stock_data


def calculate_order_quantities_matrix(consumption_data, stock_data, wanted_weeks):
    """
    Calculate order quantities using the formula:
    Order Qty = (Average Consumption × Weeks Wanted) - Current Stock
    For each item and farm
    """
    order_qty_data = []
    
    consumption_dict = {item["item_code"]: item for item in consumption_data}
    stock_dict = {item["item_code"]: item for item in stock_data}
    
    farm_fields = ["tima_1", "tima_2", "tima_3", "tima_4", "tima_5", "tima_6", "tima_7", "jangwani"]
    
    for item_code, consumption_item in consumption_dict.items():
        stock_item = stock_dict.get(item_code, {})
        
        item_data = {
            "item_code": item_code,
            "item_name": consumption_item.get("item_name", ""),
            "uom": consumption_item.get("uom", "")
        }
        
        # Calculate order quantity for each farm
        for field in farm_fields:
            avg_consumption = consumption_item.get(field, 0)
            current_stock = stock_item.get(field, 0)
            
            calculated_qty = (avg_consumption * wanted_weeks) - current_stock
            
            calculated_qty = max(0, calculated_qty)
            
            item_data[field] = calculated_qty
        
        order_qty_data.append(item_data)
    
    return order_qty_data


@frappe.whitelist()
def create_material_request(doc_name):
    """Create a Material Request based on the Order Quantity table"""
    fertilizer_order = frappe.get_doc("Fertilizer Order Sheet", doc_name)
    
    if not fertilizer_order.order_quantity:
        frappe.throw(_("No order quantities found"))
    
    # Create a new Material Request
    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Purchase"
    mr.transaction_date = datetime.now().date()
    mr.schedule_date = datetime.now().date() + timedelta(days=7)  # Default to a week from now
    mr.title = f"Fertilizer Order {fertilizer_order.name}"
    
    # Add items from order quantity table
    farms = ["tima_1", "tima_2", "tima_3", "tima_4", "tima_5", "tima_6", "tima_7", "jangwani"]
    
    for row in fertilizer_order.order_quantity:
        # For each farm with a quantity > 0, add an item
        for farm in farms:
            qty = getattr(row, farm, 0)
            if qty > 0:
                stock_uom = frappe.db.get_value("Item", row.item, "stock_uom")
                
                mr.append("items", {
                    "item_code": row.item,
                    "qty": qty,
                    "schedule_date": mr.schedule_date,
                    "warehouse": get_default_warehouse_for_farm(farm.replace("_", "")),
                    "stock_uom": stock_uom,
                    "uom": stock_uom,
                    "conversion_factor": 1.0,
                    "description": f"For farm {farm.replace('_', ' ').title()}"
                })
    
    if not mr.items:
        frappe.throw(_("No items with quantities greater than zero found"))
    
    mr.insert()
    mr.submit()
    
    # Link the Material Request back to the Fertilizer Order
    fertilizer_order.material_request = mr.name
    fertilizer_order.save()
    
    return mr.name


@frappe.whitelist()
def create_request_for_quotation(doc_name, supplier=None):
    """Create a Request for Quotation based on the Order Quantity table"""
    fertilizer_order = frappe.get_doc("Fertilizer Order Sheet", doc_name)
    
    if not fertilizer_order.order_quantity:
        frappe.throw(_("No order quantities found"))
    
    # Create a new Request for Quotation
    rfq = frappe.new_doc("Request for Quotation")
    rfq.transaction_date = datetime.now().date()
    rfq.title = f"Fertilizer Order {fertilizer_order.name}"
    
    # Get default company
    default_company = frappe.defaults.get_user_default("Company")
    rfq.company = default_company
    
    # Add items from order quantity table
    farms = ["tima_1", "tima_2", "tima_3", "tima_4", "tima_5", "tima_6", "tima_7", "jangwani"]
    
    item_totals = {}  
    
    # First pass: aggregate quantities by item
    for row in fertilizer_order.order_quantity:
        item_code = row.item
        if item_code not in item_totals:
            item_totals[item_code] = 0
            
        for farm in farms:
            qty = getattr(row, farm, 0)
            if qty > 0:
                item_totals[item_code] += qty
    
    # Get a warehouse that belongs to the company
    warehouse = get_company_warehouse(default_company)
    
    # Second pass: add items to RFQ
    for item_code, total_qty in item_totals.items():
        if total_qty > 0:
            item_name = frappe.db.get_value("Item", item_code, "item_name")
            stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
            
            # Add conversion factor of 1 explicitly
            rfq.append("items", {
                "item_code": item_code,
                "item_name": item_name,
                "qty": total_qty,
                "schedule_date": datetime.now().date() + timedelta(days=7),
                "uom": stock_uom,
                "stock_uom": stock_uom,  # Add stock UOM
                "conversion_factor": 1.0,  # Add conversion factor explicitly
                "warehouse": warehouse
            })
    
    if not rfq.items:
        frappe.throw(_("No items with quantities greater than zero found"))
    
    # Add supplier if provided
    if supplier:
        rfq.append("suppliers", {
            "supplier": supplier,
            "supplier_name": frappe.db.get_value("Supplier", supplier, "supplier_name"),
        })
    
    # Set message for supplier to prevent mandatory field error
    rfq.message_for_supplier = "Please provide a quotation for the items listed."
    
    rfq.insert()
    
    # Link the RFQ back to the Fertilizer Order Sheet
    fertilizer_order.request_for_quotation = rfq.name
    fertilizer_order.save()
    
    return rfq.name


@frappe.whitelist()
def create_purchase_order(doc_name, supplier=None):
    """Create a Purchase Order directly based on the Order Quantity table"""
    fertilizer_order = frappe.get_doc("Fertilizer Order Sheet", doc_name)
    
    if not fertilizer_order.order_quantity:
        frappe.throw(_("No order quantities found"))
    
    if not supplier:
        frappe.throw(_("Supplier is required to create a Purchase Order"))
    
    default_company = frappe.defaults.get_user_default("Company")
    
    # Create a new Purchase Order
    po = frappe.new_doc("Purchase Order")
    po.supplier = supplier
    po.company = default_company  # Set company explicitly
    po.transaction_date = datetime.now().date()
    po.schedule_date = datetime.now().date() + timedelta(days=7)
    po.title = f"Fertilizer Order {fertilizer_order.name}"
    
    # Add items from order quantity table
    farms = ["tima_1", "tima_2", "tima_3", "tima_4", "tima_5", "tima_6", "tima_7", "jangwani"]
    
    item_totals = {}  # To aggregate quantities by item
    
    # First pass: aggregate quantities by item
    for row in fertilizer_order.order_quantity:
        item_code = row.item
        if item_code not in item_totals:
            item_totals[item_code] = 0
            
        for farm in farms:
            qty = getattr(row, farm, 0)
            if qty > 0:
                item_totals[item_code] += qty
    
    # Get a warehouse that belongs to the company
    warehouse = get_company_warehouse(default_company)
    
    # Second pass: add items to PO
    for item_code, total_qty in item_totals.items():
        if total_qty > 0:
            # Get last purchase rate
            last_purchase_rate = frappe.db.get_value("Item Price", 
                {"item_code": item_code, "buying": 1, "price_list": "Standard Buying"}, 
                "price_list_rate") or 0
            
            stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
            
            po.append("items", {
                "item_code": item_code,
                "qty": total_qty,
                "schedule_date": po.schedule_date,
                "warehouse": warehouse,
                "stock_uom": stock_uom,
                "uom": stock_uom,
                "conversion_factor": 1.0,
                "rate": last_purchase_rate
            })
    
    if not po.items:
        frappe.throw(_("No items with quantities greater than zero found"))
    
    po.insert()
    
    # Link the Purchase Order to the Fertilizer Order Sheet
    fertilizer_order.purchase_order = po.name
    fertilizer_order.save()
    
    return po.name


def get_company_warehouse(company):
    """Get a warehouse belonging to the specified company"""
    # Try to get a warehouse that belongs to the company
    warehouses = frappe.get_all(
        "Warehouse", 
        filters={"company": company, "is_group": 0},
        fields=["name"],
        limit=1
    )
    
    if warehouses:
        return warehouses[0].name
    
    # Fallback to default warehouse if it belongs to the company
    default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    if default_warehouse:
        warehouse_company = frappe.db.get_value("Warehouse", default_warehouse, "company")
        if warehouse_company == company:
            return default_warehouse
    
    # If no suitable warehouse found, throw an error
    frappe.throw(_("No warehouse found for company {0}. Please create a warehouse for this company first.").format(company))


def get_default_warehouse():
    """Get default warehouse for purchases with company validation"""
    default_company = frappe.defaults.get_user_default("Company")
    default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    
    if default_warehouse:
        # Verify warehouse belongs to the company
        warehouse_company = frappe.db.get_value("Warehouse", default_warehouse, "company")
        if warehouse_company == default_company:
            return default_warehouse
    
    # Fallback to first warehouse found for the company
    warehouses = frappe.get_all(
        "Warehouse", 
        filters={"is_group": 0, "company": default_company},
        limit=1
    )
    
    if warehouses:
        return warehouses[0].name
    
    frappe.throw(_("No warehouse found for company {0}").format(default_company))


def get_default_warehouse_for_farm(farm):
    """Get the default warehouse for a farm (fertilizer store) with company validation"""
    default_company = frappe.defaults.get_user_default("Company")
    warehouse_name = f"Fertilizer Store -{farm.replace('Tima', 'T')} - TF"
    
    # Check if warehouse exists and belongs to the company
    if frappe.db.exists("Warehouse", warehouse_name):
        warehouse_company = frappe.db.get_value("Warehouse", warehouse_name, "company")
        if warehouse_company == default_company:
            return warehouse_name
    
    # Try alternative format if the first naming convention didn't work
    warehouse_name = f"Fertilizer Store - {farm.title()} - TF"
    if frappe.db.exists("Warehouse", warehouse_name):
        warehouse_company = frappe.db.get_value("Warehouse", warehouse_name, "company")
        if warehouse_company == default_company:
            return warehouse_name
    
    return get_default_warehouse()
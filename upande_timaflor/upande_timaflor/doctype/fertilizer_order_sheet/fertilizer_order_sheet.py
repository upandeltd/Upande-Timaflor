import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def get_warehouse_specific_stock():
    try:
        WAREHOUSE_MAP = {
            'Fertilizer Store -T1 - T': 'tima_1',
            'Fertilizer Store -T2 - T': 'tima_2', 
            'Fertilizer Store -T3 - T': 'tima_3',
            'Fertilizer Store -T4 - T': 'tima_4',
            'Fertilizer Store -T5 - T': 'tima_5',
            'Fertilizer Store -T6 - T': 'tima_6',
            'Fertilizer Store -T7 - T': 'tima_7',
            'Jangwani Stores - TFL': 'jangwani'
        }

        # Get all fertilizer items with proper validation
        items = frappe.get_all("Item",
            filters={"item_group": "Fertilizer", "disabled": 0},
            fields=["name", "item_name"],
            order_by="item_name"
        )

        if not items:
            frappe.log_error("No fertilizer items found", "Stock Error")
            return {"error": "No fertilizer items found in the system"}

        # Get stock data with better error handling
        stock_data = frappe.db.sql("""
            SELECT b.item_code, i.item_name, b.warehouse, SUM(b.actual_qty) as qty
            FROM `tabBin` b
            JOIN `tabItem` i ON b.item_code = i.name
            WHERE b.warehouse IN %(warehouses)s
            AND i.item_group = 'Fertilizer'
            AND i.disabled = 0
            GROUP BY b.item_code, b.warehouse
        """, {"warehouses": list(WAREHOUSE_MAP.keys())}, as_dict=1)

        # Create stock mapping
        stock_map = {}
        for entry in stock_data:
            key = (entry.item_code, entry.warehouse)
            stock_map[key] = flt(entry.qty)

        result = []
        for item in items:
            # Ensure we have proper item name fallback
            item_name = item.item_name or item.name
            
            row = {
                "item": item.name,  # This is the item code
                "item_name": item_name,  # This is the display name
                "item_code": item.name,  # Explicit item code
                "tima_1": 0.0,
                "tima_2": 0.0,
                "tima_3": 0.0,
                "tima_4": 0.0,
                "tima_5": 0.0,
                "tima_6": 0.0,
                "tima_7": 0.0,
                "jangwani": 0.0
            }

            # Populate warehouse-specific stock
            for warehouse, field in WAREHOUSE_MAP.items():
                key = (item.name, warehouse)
                row[field] = flt(stock_map.get(key, 0), 2)

            # Calculate total stock
            row["total_stock"] = flt(sum(row[field] for field in WAREHOUSE_MAP.values()), 2)
            result.append(row)

        return result

    except Exception as e:
        frappe.log_error(f"Stock Error: {str(e)}", "get_warehouse_specific_stock")
        return {"error": str(e)}

@frappe.whitelist()
def get_all_fertilizers():
    try:
        items = frappe.get_all("Item",
            filters={"item_group": "Fertilizer", "disabled": 0},
            fields=["name", "item_name"],
            order_by="item_name"
        )
        
        if not items:
            return {"error": "No fertilizer items found"}
        
        result = []
        for item in items:
            item_name = item.item_name or item.name
            result.append({
                "item_code": item.name,  # The actual item code
                "item_name": item_name,  # The display name
                "name": item_name  # For backward compatibility
            })
        
        return result

    except Exception as e:
        frappe.log_error(f"Fertilizer Error: {str(e)}", "get_all_fertilizers")
        return {"error": str(e)}

@frappe.whitelist()
def debug_fertilizer_data():
    try:
        items = frappe.db.sql("""
            SELECT name as item_code, item_name, disabled, item_group
            FROM `tabItem`
            WHERE item_group = 'Fertilizer'
            ORDER BY item_name
        """, as_dict=1)

        stock = frappe.db.sql("""
            SELECT b.item_code, i.item_name, b.warehouse, b.actual_qty
            FROM `tabBin` b
            JOIN `tabItem` i ON b.item_code = i.name
            WHERE i.item_group = 'Fertilizer'
            AND b.actual_qty != 0
            ORDER BY i.item_name, b.warehouse
        """, as_dict=1)

        warehouses = frappe.db.sql("""
            SELECT name, disabled
            FROM `tabWarehouse`
            WHERE name LIKE '%Fertilizer%' OR name LIKE '%Jangwani%'
            ORDER BY name
        """, as_dict=1)

        return {
            "items": items,
            "items_count": len(items),
            "stock": stock,
            "stock_entries": len(stock),
            "warehouses": warehouses
        }

    except Exception as e:
        frappe.log_error(f"Debug Error: {str(e)}", "debug_fertilizer_data")
        return {"error": str(e)}

@frappe.whitelist()
def validate_fertilizer_setup():
    try:
        warehouse_list = [
            'Fertilizer Store -T1 - T',
            'Fertilizer Store -T2 - T', 
            'Fertilizer Store -T3 - T',
            'Fertilizer Store -T4 - T',
            'Fertilizer Store -T5 - T',
            'Fertilizer Store -T6 - T',
            'Fertilizer Store -T7 - T',
            'Jangwani Stores - TFL'
        ]
        
        existing_warehouses = []
        missing_warehouses = []
        
        for warehouse in warehouse_list:
            if frappe.db.exists("Warehouse", warehouse):
                existing_warehouses.append(warehouse)
            else:
                missing_warehouses.append(warehouse)
        
        # Also check for fertilizer items
        fertilizer_count = frappe.db.count("Item", {"item_group": "Fertilizer", "disabled": 0})
        
        return {
            "existing_warehouses": existing_warehouses,
            "missing_warehouses": missing_warehouses,
            "fertilizer_items_count": fertilizer_count
        }
        
    except Exception as e:
        frappe.log_error(f"Validate Setup Error: {str(e)}", "validate_fertilizer_setup")
        return {"error": str(e)}

@frappe.whitelist()
def cleanup_consumption_table(docname):
    """Clean up consumption table by removing rows with missing item names"""
    try:
        doc = frappe.get_doc("Fertilizer Order Sheet", docname)
        
        # Get valid fertilizer items
        valid_items = frappe.get_all("Item",
            filters={"item_group": "Fertilizer", "disabled": 0},
            fields=["name", "item_name"]
        )
        
        valid_item_codes = {item.name for item in valid_items}
        valid_item_names = {item.item_name or item.name for item in valid_items}
        
        # Filter out invalid rows
        valid_rows = []
        for row in doc.weekly_average_consumption:
            if (row.item and row.item in valid_item_codes) or \
               (row.item_name and row.item_name in valid_item_names):
                valid_rows.append(row)
        
        # Update the table
        doc.weekly_average_consumption = valid_rows
        doc.save()
        
        return {
            "success": True,
            "message": f"Cleaned up consumption table. Kept {len(valid_rows)} valid rows."
        }
        
    except Exception as e:
        frappe.log_error(f"Cleanup Error: {str(e)}", "cleanup_consumption_table")
        return {"error": str(e)}
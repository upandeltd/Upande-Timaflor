frappe.ui.form.on('Ordering Sheet', {
    refresh: function(frm) {
        // Modified PO Creation Button with Supplier Dialog
        frm.add_custom_button(__('Create Purchase Order'), function() {
            if(!frm.doc.supplier) {
                // Show supplier selection dialog if not set
                show_supplier_dialog(frm);
            } else {
                // Proceed directly if supplier exists
                create_po(frm);
            }
        }, __('Create'));
        
        // Add a button to manually calculate order quantities
        frm.add_custom_button(__('Calculate Order Quantities'), function() {
            calculate_order_quantities(frm);
        });
    },

    before_save: function(frm) {
        console.log("Trigger: before_save");
        if (!frm.doc.daily_average_consumptiondays || !frm.doc.table_bvnr) {
            console.log("Missing Required Data");
            return;
        }

        // Collect all item codes from the table
        let item_codes = frm.doc.table_bvnr.map(row => row.item);
        
        // Fetch consumption data for all three types
        fetch_consumption_data(frm, item_codes).then(() => {
            // No automatic calculation of order quantities to delink them
            frm.refresh_field("table_bvnr");
            frm.refresh_field("daily_minimum_consumption");
            frm.refresh_field("daily_maximum_consumption");
        });
    }
});

// Function to fetch all consumption data types
function fetch_consumption_data(frm, item_codes) {
    const from_date = frappe.datetime.add_days(frappe.datetime.nowdate(), -frm.doc.daily_average_consumptiondays);
    const to_date = frappe.datetime.nowdate();
    
    return new Promise((resolve) => {
        frappe.call({
            method: 'upande_timaflor.upande_timaflor.doctype.ordering_sheet.ordering_sheet.get_all_consumption_data',
            args: {
                item_codes: item_codes,
                from_date: from_date,
                to_date: to_date
            },
            callback: function(r) {
                if (!r.exc && r.message) {
                    // Process average consumption data
                    process_consumption_data(frm, r.message.average, "table_bvnr", "avg");
                    
                    // Process minimum consumption data
                    process_consumption_data(frm, r.message.minimum, "daily_minimum_consumption", "minimum");
                    
                    // Process maximum consumption data
                    process_consumption_data(frm, r.message.maximum, "daily_maximum_consumption", "maximum");
                }
                resolve();
            }
        });
    });
}

// Function to process different types of consumption data
function process_consumption_data(frm, data, table_field, data_type) {
    if (!data || !frm.doc[table_field]) return;
    
    // Clear existing data
    frm.doc[table_field] = [];
    
    // Field name mapping based on data type
    const fieldMap = {
        "avg": {
            "Tima1": "t1_avg",
            "Tima2": "t2_avg",
            "Tima3": "t3_avg",
            "Tima4": "t4_avg",
            "Tima5": "t5_avg",
            "Tima6": "t6_avg",
            "Tima7": "t7_avg",
            "Jangwani": "jangwani_avg"
        },
        "minimum": {
            "Tima1": "tima_1_minimum",
            "Tima2": "tima_2_minimum",
            "Tima3": "tima_3_minimum",
            "Tima4": "tima_4_minimum",
            "Tima5": "tima_5_minimum",
            "Tima6": "tima_6_minimum",
            "Tima7": "tima_7_minimum",
            "Jangwani": "jangwani_minimum"
        },
        "maximum": {
            "Tima1": "tima_1_daily_avg",
            "Tima2": "tima_2_daily_avg",
            "Tima3": "tima_3_daily_avg",
            "Tima4": "tima_4_daily_avg",
            "Tima5": "tima_5_daily_avg",
            "Tima6": "tima_6_daily_avg",
            "Tima7": "tima_7_daily_avg",
            "Jangwani": "jangwani_daily_avg"
        }
    };
    
    // Process each item's data
    Object.entries(data).forEach(([item_code, farm_data]) => {
        const row = frappe.model.add_child(frm.doc, table_field.charAt(0).toUpperCase() + table_field.slice(1), table_field);
        row.item = item_code;
        
        // Initialize with zeros
        Object.values(fieldMap[data_type]).forEach(field => {
            row[field] = 0;
        });
        
        // Set values from data
        Object.entries(farm_data).forEach(([farm, value]) => {
            const field = fieldMap[data_type][farm];
            if (field) row[field] = value;
        });
    });
    
    frm.refresh_field(table_field);
}

// New Dialog Handling Functions
function show_supplier_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Select Supplier'),
        fields: [{
            label: __('Supplier'),
            fieldname: 'supplier',
            fieldtype: 'Link',
            options: 'Supplier',
            reqd: 1
        }],
        primary_action: function(values) {
            dialog.hide();
            create_po(frm, values.supplier);
        }
    });
    dialog.show();
}

function create_po(frm, supplier) {
    frappe.confirm(__('Create Purchase Order from this sheet?'), () => {
        frm.call('create_purchase_order', {
            supplier: supplier || frm.doc.supplier
        }).then((r) => {
            if(r.message) {
                frappe.show_alert({
                    message: __('PO {0} created', [r.message]),
                    indicator: 'green'
                });
                frappe.set_route('Form', 'Purchase Order', r.message);
            }
        });
    });
}

// Modified Order Quantity Calculation (now manual)
function calculate_order_quantities(frm) {
    if (!frm.doc.ordering_quantity) {
        frappe.throw(__('Please set an Ordering Quantity first'));
        return;
    }
    
    // Ask which consumption data to use for calculation
    const dialog = new frappe.ui.Dialog({
        title: __('Calculate Order Quantities'),
        fields: [{
            label: __('Base Calculation On'),
            fieldname: 'calculation_base',
            fieldtype: 'Select',
            options: 'Average Consumption\nMinimum Consumption\nMaximum Consumption\nCustom Values',
            default: 'Average Consumption',
            reqd: 1
        }],
        primary_action: function(values) {
            dialog.hide();
            
            // Clear existing order quantities
            frm.doc.order_quantity = [];
            
            let source_table, field_map;
            
            switch(values.calculation_base) {
                case 'Average Consumption':
                    source_table = frm.doc.table_bvnr;
                    field_map = {
                        't1_avg': 'tima_1',
                        't2_avg': 'tima_2',
                        't3_avg': 'tima_3',
                        't4_avg': 'tima_4',
                        't5_avg': 'tima_5',
                        't6_avg': 'tima_6',
                        't7_avg': 'tima_7',
                        'jangwani_avg': 'jangwani'
                    };
                    break;
                    
                case 'Minimum Consumption':
                    source_table = frm.doc.daily_minimum_consumption;
                    field_map = {
                        'tima_1_minimum': 'tima_1',
                        'tima_2_minimum': 'tima_2',
                        'tima_3_minimum': 'tima_3',
                        'tima_4_minimum': 'tima_4',
                        'tima_5_minimum': 'tima_5',
                        'tima_6_minimum': 'tima_6',
                        'tima_7_minimum': 'tima_7',
                        'jangwani_minimum': 'jangwani'
                    };
                    break;
                    
                case 'Maximum Consumption':
                    source_table = frm.doc.daily_maximum_consumption;
                    field_map = {
                        'tima_1_daily_avg': 'tima_1',
                        'tima_2_daily_avg': 'tima_2',
                        'tima_3_daily_avg': 'tima_3',
                        'tima_4_daily_avg': 'tima_4',
                        'tima_5_daily_avg': 'tima_5',
                        'tima_6_daily_avg': 'tima_6',
                        'tima_7_daily_avg': 'tima_7',
                        'jangwani_daily_avg': 'jangwani'
                    };
                    break;
                    
                case 'Custom Values':
                    // Allow user to enter custom values
                    show_custom_values_dialog(frm);
                    return;
            }
            
            // Calculate order quantities based on selected source
            if (source_table && source_table.length > 0) {
                source_table.forEach(source_row => {
                    let order_row = frappe.model.add_child(frm.doc, "Order Quantity", "order_quantity");
                    order_row.item = source_row.item;
                    
                    // Apply calculation for each field
                    Object.entries(field_map).forEach(([source_field, target_field]) => {
                        order_row[target_field] = (source_row[source_field] || 0) * frm.doc.ordering_quantity;
                    });
                });
                
                frm.refresh_field("order_quantity");
                frappe.show_alert({
                    message: __('Order quantities calculated based on ' + values.calculation_base),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint(__('No source data found for ' + values.calculation_base));
            }
        }
    });
    dialog.show();
}

// Dialog for custom values entry
function show_custom_values_dialog(frm) {
    // Get unique items from any existing consumption table
    let items = [];
    if (frm.doc.table_bvnr && frm.doc.table_bvnr.length > 0) {
        items = frm.doc.table_bvnr.map(row => ({
            label: row.item,
            value: row.item
        }));
    } else if (frm.doc.daily_minimum_consumption && frm.doc.daily_minimum_consumption.length > 0) {
        items = frm.doc.daily_minimum_consumption.map(row => ({
            label: row.item,
            value: row.item
        }));
    } else if (frm.doc.daily_maximum_consumption && frm.doc.daily_maximum_consumption.length > 0) {
        items = frm.doc.daily_maximum_consumption.map(row => ({
            label: row.item,
            value: row.item
        }));
    }
    
    if (items.length === 0) {
        frappe.msgprint(__('No items found for custom order calculation'));
        return;
    }
    
    const dialog = new frappe.ui.Dialog({
        title: __('Enter Custom Order Values'),
        fields: [
            {
                label: __('Item'),
                fieldname: 'item',
                fieldtype: 'Select',
                options: items,
                reqd: 1
            },
            {
                label: __('TIMA 1'),
                fieldname: 'tima_1',
                fieldtype: 'Float',
                default: 0
            },
            {
                label: __('TIMA 2'),
                fieldname: 'tima_2',
                fieldtype: 'Float',
                default: 0
            },
            {
                label: __('TIMA 3'),
                fieldname: 'tima_3',
                fieldtype: 'Float',
                default: 0
            },
            {
                label: __('TIMA 4'),
                fieldname: 'tima_4',
                fieldtype: 'Float',
                default: 0
            },
            {
                label: __('TIMA 5'),
                fieldname: 'tima_5',
                fieldtype: 'Float',
                default: 0
            },
            {
                label: __('TIMA 6'),
                fieldname: 'tima_6',
                fieldtype: 'Float',
                default: 0
            },
            {
                label: __('TIMA 7'),
                fieldname: 'tima_7',
                fieldtype: 'Float',
                default: 0
            },
            {
                label: __('Jangwani'),
                fieldname: 'jangwani',
                fieldtype: 'Float',
                default: 0
            }
        ],
        primary_action: function(values) {
            // Add to order quantities
            let order_row = frappe.model.add_child(frm.doc, "Order Quantity", "order_quantity");
            order_row.item = values.item;
            order_row.tima_1 = values.tima_1;
            order_row.tima_2 = values.tima_2;
            order_row.tima_3 = values.tima_3;
            order_row.tima_4 = values.tima_4;
            order_row.tima_5 = values.tima_5;
            order_row.tima_6 = values.tima_6;
            order_row.tima_7 = values.tima_7;
            order_row.jangwani = values.jangwani;
            
            frm.refresh_field("order_quantity");
            
            // Reset the dialog to enter another item
            dialog.fields_dict.tima_1.set_value(0);
            dialog.fields_dict.tima_2.set_value(0);
            dialog.fields_dict.tima_3.set_value(0);
            dialog.fields_dict.tima_4.set_value(0);
            dialog.fields_dict.tima_5.set_value(0);
            dialog.fields_dict.tima_6.set_value(0);
            dialog.fields_dict.tima_7.set_value(0);
            dialog.fields_dict.jangwani.set_value(0);
            
            frappe.show_alert({
                message: __('Item added to order quantities'),
                indicator: 'green'
            });
        },
        primary_action_label: __('Add Item'),
        secondary_action: function() {
            dialog.hide();
        },
        secondary_action_label: __('Done')
    });
    dialog.show();
}
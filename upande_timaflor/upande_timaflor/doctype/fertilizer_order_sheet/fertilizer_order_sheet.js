// Copyright (c) 2025, newton@upande.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Fertilizer Order Sheet", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Fertilizer Order Sheet', {
    refresh: function(frm) {
        frm.add_custom_button(__('Calculate Order Quantities'), function() {
            calculate_order_quantities(frm);
        });

        // Add button to copy data to a Material Request
        frm.add_custom_button(__('Create Material Request'), function() {
            create_material_request(frm);
        }).addClass('btn-primary');
    },
    
    average_consumption: function(frm) {
        // Clear child tables when input changes
        frm.clear_table('weekly_average_consumption');
        frm.clear_table('stock_levels');
        frm.clear_table('order_quantity');
        frm.refresh();
    },
    
    stock_wantedweeks: function(frm) {
        // Recalculate order quantities when weeks change if we have data
        if(frm.doc.weekly_average_consumption && frm.doc.weekly_average_consumption.length > 0 && 
           frm.doc.stock_levels && frm.doc.stock_levels.length > 0) {
            calculate_order_quantities(frm);
        }
    }
});

function calculate_order_quantities(frm) {
    if(!frm.doc.average_consumption || !frm.doc.stock_wantedweeks) {
        frappe.msgprint(__('Please enter Average Consumption and Stock Wanted(Weeks)'));
        return;
    }
    
    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.calculate_fertilizer_matrix_data',
        args: {
            'average_consumption': frm.doc.average_consumption,
            'stock_wantedweeks': frm.doc.stock_wantedweeks
        },
        freeze: true,
        freeze_message: __('Calculating fertilizer data...'),
        callback: function(r) {
            if(r.message) {
                // Clear existing data
                frm.clear_table('weekly_average_consumption');
                frm.clear_table('stock_levels');
                frm.clear_table('order_quantity');
                
                // Update average consumption child table
                r.message.consumption.forEach(function(item) {
                    let row = frm.add_child('weekly_average_consumption');
                    row.item = item.item_code;
                    row.tima_1 = item.tima_1;
                    row.tima_2 = item.tima_2;
                    row.tima_3 = item.tima_3;
                    row.tima_4 = item.tima_4;
                    row.tima_5 = item.tima_5;
                    row.tima_6 = item.tima_6;
                    row.tima_7 = item.tima_7;
                    row.jangwani = item.jangwani;
                });
                
                // Update stock levels child table
                r.message.stock.forEach(function(item) {
                    let row = frm.add_child('stock_levels');
                    row.item = item.item_code;
                    row.tima_1 = item.tima_1;
                    row.tima_2 = item.tima_2;
                    row.tima_3 = item.tima_3;
                    row.tima_4 = item.tima_4;
                    row.tima_5 = item.tima_5;
                    row.tima_6 = item.tima_6;
                    row.tima_7 = item.tima_7;
                    row.jangwani = item.jangwani;
                });
                
                // Update order quantities child table
                r.message.order_qty.forEach(function(item) {
                    let row = frm.add_child('order_quantity');
                    row.item = item.item_code;
                    row.tima_1 = item.tima_1;
                    row.tima_2 = item.tima_2;
                    row.tima_3 = item.tima_3;
                    row.tima_4 = item.tima_4;
                    row.tima_5 = item.tima_5;
                    row.tima_6 = item.tima_6;
                    row.tima_7 = item.tima_7;
                    row.jangwani = item.jangwani;
                });
                
                frm.refresh();
                frappe.show_alert(__('Order quantities calculated successfully'));
            }
        }
    });
}

function create_material_request(frm) {
    if(!frm.doc.order_quantity || frm.doc.order_quantity.length === 0) {
        frappe.msgprint(__('Please calculate order quantities first'));
        return;
    }
    
    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.create_material_request',
        args: {
            'doc_name': frm.docname
        },
        freeze: true,
        freeze_message: __('Creating Material Request...'),
        callback: function(r) {
            if(r.message) {
                frappe.show_alert(__('Material Request {0} created', [r.message]));
                frappe.set_route('Form', 'Material Request', r.message);
            }
        }
    });
}
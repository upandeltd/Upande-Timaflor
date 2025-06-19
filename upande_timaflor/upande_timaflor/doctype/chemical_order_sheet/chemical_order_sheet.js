// Copyright (c) 2025, newton@upande.com
// For license information, please see license.txt

let farm_area_warning_shown = false;
let item_stock_cache = {};

frappe.ui.form.on('Chemical Order Sheet', {
    refresh: function(frm) {
        // Pre-fetch stock quantities for all chemicals
        frappe.call({
            method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.get_stock_for_all_chemicals',
            callback: function(r) {
                if (r.message) {
                    item_stock_cache = r.message;
                    console.log("Stock cache loaded:", item_stock_cache);
                }
            }
        });
        
        // Add All Chemicals Button
        frm.add_custom_button(__('Add All Chemicals'), function() {
            if (!frm.doc.farm_area_to_spray || frm.doc.farm_area_to_spray.length === 0) {
                if (!farm_area_warning_shown) {
                    frappe.msgprint(__('Please add at least one farm area before adding chemicals.'));
                    farm_area_warning_shown = true;
                }
                return;
            }

            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.get_all_chemicals_with_details',
                freeze: true,
                freeze_message: __('Fetching chemicals...'),
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frappe.confirm(
                            __('This will replace your current chemicals list. Continue?'),
                            function() {
                                frm.clear_table('spray_details');
                                
                                r.message.forEach(chem => {
                                    let row = frm.add_child('spray_details');
                                    row.chemical = chem.name;
                                    row.chemical_name = chem.item_name;
                                    row.target = chem.target || '';
                                    row.application_rate_per_hectare = chem.application_rate || 0;
                                    row.required_number_of_sprays = chem.required_sprays || 0;
                                    row.number_of_sprays = chem.number_of_sprays || chem.required_sprays || 0;
                                });
                                
                                frm.refresh_field('spray_details');
                                frappe.show_alert(__('Added ' + r.message.length + ' chemicals to the list'));
                                setTimeout(() => frm.trigger('calculate_orders'), 500);
                            }
                        );
                    } else {
                        frappe.msgprint(__('No chemicals found in the system.'));
                    }
                },
                error: function(r) {
                    frappe.msgprint(__('Error fetching chemicals. Please try again.'));
                }
            });
        });

        // Calculate Button
        frm.add_custom_button(__('Calculate Order Quantities'), function() {
            if (!frm.doc.farm_area_to_spray || frm.doc.farm_area_to_spray.length === 0) {
                frappe.msgprint(__('Please add at least one farm area before calculating.'));
                return;
            }
            if (!frm.doc.spray_details || frm.doc.spray_details.length === 0) {
                frappe.msgprint(__('Please add at least one chemical before calculating.'));
                return;
            }

            frm.trigger('calculate_orders');
        });

        // Create RFQ & PO Buttons
        frm.add_custom_button(__('Create RFQ'), function() {
            create_request_for_quotation(frm);
        }, __('Create'));

        frm.add_custom_button(__('Create PO'), function() {
            create_purchase_order(frm, false);
        }, __('Create'));
    },

    validate: function(frm) {
        return true; // Calculation is triggered manually
    },

    calculate_orders: function(frm) {
        if (frm.doc.farm_area_to_spray?.length > 0 && frm.doc.spray_details?.length > 0) {
            frappe.show_progress(__('Calculating Orders'), 0, 100);

            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.calculate_order_quantities',
                args: { 
                    doc: frm.doc,
                    stock_data: item_stock_cache
                },
                freeze: true,
                freeze_message: __('Calculating order quantities...'),
                callback: function(r) {
                    frappe.hide_progress();

                    if (r.message) {
                        frm.clear_table('order_detail');
                        r.message.forEach(order => {
                            try {
                                let row = frm.add_child('order_detail');
                                Object.assign(row, order);
                            } catch (e) {
                                console.error("Error adding order detail:", order.item, e);
                            }
                        });
                        frm.refresh_field('order_detail');
                        frm.trigger('calculate_totals');
                        frappe.show_alert(__('Order quantities calculated'));
                    } else {
                        frappe.msgprint(__('No order details were calculated. Check your data and try again.'));
                    }
                },
                error: function(r) {
                    frappe.hide_progress();
                    frappe.msgprint(__('An error occurred while calculating order quantities.'));
                }
            });
        } else {
            frappe.msgprint(__('Please add farm areas and chemicals before calculating'));
        }
    },

    calculate_totals: function(frm) {
        let total = 0;
        let promises = [];

        if (frm.doc.order_detail?.length > 0) {
            frm.doc.order_detail.forEach(item => {
                if (!item.item) return;

                let total_qty = ['tima_1','tima_2','tima_3','tima_4','tima_5','tima_6','tima_7','jangwani']
                    .map(f => parseFloat(item[f] || 0)).reduce((a, b) => a + b, 0);

                if (total_qty > 0) {
                    promises.push(new Promise(resolve => {
                        frappe.call({
                            method: 'frappe.client.get_value',
                            args: {
                                doctype: 'Item',
                                filters: { name: item.item },
                                fieldname: 'valuation_rate'
                            },
                            callback: function(r) {
                                resolve(r.message?.valuation_rate ? total_qty * r.message.valuation_rate : 0);
                            },
                            error: function() {
                                resolve(0);
                            }
                        });
                    }));
                }
            });

            Promise.all(promises).then(values => {
                total = values.reduce((sum, val) => sum + val, 0);
                frm.set_value('total_order_amount', total);
            });
        } else {
            frm.set_value('total_order_amount', 0);
        }
    }
});

// Handle changes to spray details
frappe.ui.form.on('Spray Details', {
    chemical: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.chemical) {
            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.get_chemical_details',
                args: { item_code: row.chemical },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'chemical_name', r.message.item_name);
                        frappe.model.set_value(cdt, cdn, 'target', r.message.target || '');
                        frappe.model.set_value(cdt, cdn, 'application_rate_per_hectare', r.message.application_rate || 0);
                        frappe.model.set_value(cdt, cdn, 'required_number_of_sprays', r.message.required_sprays || 0);
                        frappe.model.set_value(cdt, cdn, 'number_of_sprays', r.message.number_of_sprays || r.message.required_sprays || 0);
                        frm.refresh_field('spray_details');
                        
                        // Auto-calculate
                        setTimeout(() => {
                            if (frm.doc.farm_area_to_spray?.length > 0) {
                                frm.trigger('calculate_orders');
                            }
                        }, 500);
                    }
                }
            });
        }
    },
    
    application_rate_per_hectare: function(frm, cdt, cdn) {
        setTimeout(() => {
            if (frm.doc.farm_area_to_spray?.length > 0) {
                frm.trigger('calculate_orders');
            }
        }, 500);
    },
    
    number_of_sprays: function(frm, cdt, cdn) {
        setTimeout(() => {
            if (frm.doc.farm_area_to_spray?.length > 0) {
                frm.trigger('calculate_orders');
            }
        }, 500);
    }
});

frappe.ui.form.on('Area To Spray', {
    farm_area_to_spray_add: function(frm, cdt, cdn) {
        setTimeout(() => {
            if (frm.doc.spray_details?.length > 0) {
                frm.trigger('calculate_orders');
            }
        }, 1000);
    },
    
    tima_1: function(frm, cdt, cdn) { trigger_auto_calc(frm); },
    tima_2: function(frm, cdt, cdn) { trigger_auto_calc(frm); },
    tima_3: function(frm, cdt, cdn) { trigger_auto_calc(frm); },
    tima_4: function(frm, cdt, cdn) { trigger_auto_calc(frm); },
    tima_5: function(frm, cdt, cdn) { trigger_auto_calc(frm); },
    tima_6: function(frm, cdt, cdn) { trigger_auto_calc(frm); },
    tima_7: function(frm, cdt, cdn) { trigger_auto_calc(frm); },
    jangwani: function(frm, cdt, cdn) { trigger_auto_calc(frm); }
});

function trigger_auto_calc(frm) {
    setTimeout(() => {
        if (frm.doc.spray_details?.length > 0 && frm.doc.farm_area_to_spray?.length > 0) {
            frm.trigger('calculate_orders');
        }
    }, 500);
}

function create_request_for_quotation(frm) {
    if (!frm.doc.order_detail || frm.doc.order_detail.length === 0) {
        frappe.msgprint(__('Please calculate order quantities first.'));
        return;
    }

    let items_to_order = [];

    frm.doc.order_detail.forEach(item => {
        if (!item.item) return;
        let total_qty = ['tima_1','tima_2','tima_3','tima_4','tima_5','tima_6','tima_7','jangwani']
            .map(f => parseFloat(item[f] || 0)).reduce((a, b) => a + b, 0);
        if (total_qty > 0) {
            items_to_order.push({
                item_code: item.item,
                item_name: item.item_name || item.item,
                qty: total_qty,
                schedule_date: frappe.datetime.add_days(frappe.datetime.nowdate(), 7)
            });
        }
    });

    if (items_to_order.length === 0) {
        frappe.msgprint(__('No items with quantities to order.'));
        return;
    }

    frappe.model.with_doctype('Request for Quotation', function() {
        let rfq = frappe.model.get_new_doc('Request for Quotation');
        rfq.transaction_date = frappe.datetime.nowdate();
        rfq.chemical_order_sheet = frm.doc.name;

        items_to_order.forEach(item => {
            let rfq_item = frappe.model.add_child(rfq, 'items');
            rfq_item.item_code = item.item_code;
            rfq_item.item_name = item.item_name;
            rfq_item.qty = item.qty;
            rfq_item.schedule_date = item.schedule_date;
        });

        frappe.set_route('Form', rfq.doctype, rfq.name);
    });
}

function create_purchase_order(frm, require_supplier = true) {
    if (!frm.doc.order_detail || frm.doc.order_detail.length === 0) {
        frappe.msgprint(__('Please calculate order quantities first.'));
        return;
    }

    let items_to_order = [];

    frm.doc.order_detail.forEach(item => {
        if (!item.item) return;
        let total_qty = ['tima_1','tima_2','tima_3','tima_4','tima_5','tima_6','tima_7','jangwani']
            .map(f => parseFloat(item[f] || 0)).reduce((a, b) => a + b, 0);
        if (total_qty > 0) {
            items_to_order.push({
                item_code: item.item,
                item_name: item.item_name || item.item,
                qty: total_qty,
                schedule_date: frappe.datetime.add_days(frappe.datetime.nowdate(), 7)
            });
        }
    });

    if (items_to_order.length === 0) {
        frappe.msgprint(__('No items with quantities to order.'));
        return;
    }

    if (require_supplier) {
        let d = new frappe.ui.Dialog({
            title: __('Create Purchase Order'),
            fields: [{
                label: __('Supplier'),
                fieldname: 'supplier',
                fieldtype: 'Link',
                options: 'Supplier',
                reqd: 1
            }],
            primary_action_label: __('Create'),
            primary_action(values) {
                create_po_with_items(frm, items_to_order, values.supplier);
                d.hide();
            }
        });
        d.show();
    } else {
        create_po_with_items(frm, items_to_order);
    }
}

function create_po_with_items(frm, items_to_order, supplier = null) {
    frappe.model.with_doctype('Purchase Order', function() {
        let po = frappe.model.get_new_doc('Purchase Order');
        if (supplier) po.supplier = supplier;
        po.transaction_date = frappe.datetime.nowdate();
        po.chemical_order_sheet = frm.doc.name;

        items_to_order.forEach(item => {
            let po_item = frappe.model.add_child(po, 'items');
            po_item.item_code = item.item_code;
            po_item.item_name = item.item_name;
            po_item.qty = item.qty;
            po_item.schedule_date = item.schedule_date;
        });

        frappe.set_route('Form', po.doctype, po.name);
    });
}
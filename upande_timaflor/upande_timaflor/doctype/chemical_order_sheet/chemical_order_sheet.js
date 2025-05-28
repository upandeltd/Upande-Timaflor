// Copyright (c) 2025, newton@upande.com
// For license information, please see license.txt

let farm_area_warning_shown = false;

frappe.ui.form.on('Chemical Order Sheet', {
    refresh: function(frm) {
        // Add All Chemicals Button - WITH DEBUG
        frm.add_custom_button(__('Add All Chemicals'), function() {
            if (!frm.doc.farm_area_to_spray || frm.doc.farm_area_to_spray.length === 0) {
                if (!farm_area_warning_shown) {
                    frappe.msgprint(__('Please add at least one farm area before adding chemicals.'));
                    farm_area_warning_shown = true;
                }
                return;
            }

            console.log("=== DEBUG: Starting Add All Chemicals ===");
            console.log("Calling get_all_chemicals method...");

            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.get_all_chemicals',
                freeze: true,
                freeze_message: __('Fetching chemicals...'),
                callback: function(r) {
                    console.log("=== DEBUG: Method Response ===");
                    console.log("Full response object:", r);
                    console.log("Response message:", r.message);
                    console.log("Message type:", typeof r.message);
                    console.log("Message length:", r.message ? r.message.length : 'null/undefined');
                    console.log("Is array?", Array.isArray(r.message));
                    
                    if (r.message && r.message.length > 0) {
                        console.log("SUCCESS: Chemicals found:", r.message.length);
                        console.log("First few chemicals:", r.message.slice(0, 5));
                        
                        frappe.confirm(
                            __('This will replace your current chemicals list. Continue?'),
                            function() {
                                console.log("User confirmed, adding chemicals...");
                                frm.clear_table('spray_details');
                                
                                let added_count = 0;
                                r.message.forEach(function(item, index) {
                                    try {
                                        console.log(`Adding chemical ${index + 1}:`, item);
                                        let row = frm.add_child('spray_details');
                                        row.chemical = item.name;
                                        row.application_rate_per_hectare = 1;
                                        row.required_number_of_sprays = 1;
                                        row.number_of_sprays = 1;
                                        added_count++;
                                    } catch (e) {
                                        console.error("Error adding chemical:", item.name, e);
                                    }
                                });
                                
                                console.log(`Successfully added ${added_count} chemicals`);
                                frm.refresh_field('spray_details');
                                frappe.show_alert(__('Added ' + added_count + ' chemicals to the list'));
                                setTimeout(() => frm.trigger('calculate_orders'), 500);
                            }
                        );
                    } else {
                        console.log("PROBLEM: No chemicals returned");
                        console.log("Testing direct database query...");
                        
                        // Test with direct frappe.client.get_list
                        frappe.call({
                            method: 'frappe.client.get_list',
                            args: {
                                doctype: 'Item',
                                filters: {'item_group': 'Chemical'},
                                fields: ['name', 'item_name'],
                                limit_page_length: 10
                            },
                            callback: function(test_r) {
                                console.log("=== DEBUG: Direct Query Test ===");
                                console.log("Direct query result:", test_r);
                                
                                if (test_r.message && test_r.message.length > 0) {
                                    frappe.msgprint({
                                        title: __('Debug Info'),
                                        message: __('Found chemicals via direct query but not via custom method. Custom method may have an error. Check console logs and server error logs.'),
                                        indicator: 'orange'
                                    });
                                } else {
                                    frappe.msgprint({
                                        title: __('Debug Info'),
                                        message: __('No chemicals found even with direct query. Check if items are actually assigned to Chemical item group and are enabled.'),
                                        indicator: 'red'
                                    });
                                }
                            },
                            error: function(test_err) {
                                console.log("Direct query error:", test_err);
                            }
                        });
                        
                        frappe.msgprint(__('No chemicals found in the system.'));
                    }
                },
                error: function(r) {
                    console.log("=== DEBUG: Method Error ===");
                    console.error("Error calling get_all_chemicals:", r);
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Error calling get_all_chemicals method. Check console and server logs for details.'),
                        indicator: 'red'
                    });
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
            if (!frm.calculate_without_popup) frappe.show_progress(__('Calculating Orders'), 0, 100);

            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.calculate_order_quantities',
                args: { doc: frm.doc },
                freeze: !frm.calculate_without_popup,
                freeze_message: __('Calculating order quantities...'),
                callback: function(r) {
                    if (!frm.calculate_without_popup) frappe.hide_progress();

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

                        if (!frm.calculate_without_popup)
                            frappe.show_alert(__('Order quantities calculated'));
                    } else if (!frm.calculate_without_popup) {
                        frappe.msgprint(__('No order details were calculated. Check your data and try again.'));
                    }
                },
                error: function(r) {
                    if (!frm.calculate_without_popup) {
                        frappe.hide_progress();
                        console.error("Error in calculate_orders:", r);
                        frappe.msgprint(__('An error occurred while calculating order quantities.'));
                    }
                }
            });
        } else if (!frm.calculate_without_popup) {
            frappe.msgprint(__('Please add farm areas and chemicals before calculating'));
        }
    },

    calculate_totals: function(frm) {
        let total = 0;
        let promises = [];

        if (frm.doc.order_detail?.length > 0) {
            frm.doc.order_detail.forEach(item => {
                if (!item.item) return;

                let qty = ['tima_1','tima_2','tima_3','tima_4','tima_5','tima_6','tima_7','jangwani']
                    .map(f => parseFloat(item[f] || 0)).reduce((a, b) => a + b, 0);

                if (qty > 0) {
                    promises.push(new Promise(resolve => {
                        frappe.call({
                            method: 'frappe.client.get_value',
                            args: {
                                doctype: 'Item',
                                filters: { name: item.item },
                                fieldname: 'valuation_rate'
                            },
                            callback: function(r) {
                                resolve(r.message?.valuation_rate ? qty * r.message.valuation_rate : 0);
                            },
                            error: function() {
                                console.warn(`Error fetching valuation rate for item: ${item.item}`);
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

frappe.ui.form.on('Area To Spray', {
    farm_area_to_spray_add: function(frm, cdt, cdn) {
        // Optional: Auto-trigger calculation when new row added
        setTimeout(() => frm.trigger('calculate_orders'), 1000);
    }
});

// DEBUG: Add a test button to directly test the method
frappe.ui.form.on('Chemical Order Sheet', {
    refresh: function(frm) {
        // Add the existing buttons first (the code above handles this)
        
        // Add a debug test button
        frm.add_custom_button(__('DEBUG: Test Method'), function() {
            console.log("=== DEBUG: Testing get_all_chemicals method directly ===");
            
            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.get_all_chemicals',
                callback: function(r) {
                    console.log("Direct method test result:", r);
                    frappe.msgprint({
                        title: 'Debug Test Result',
                        message: `Found ${r.message ? r.message.length : 0} chemicals. Check console for details.`,
                        indicator: r.message && r.message.length > 0 ? 'green' : 'red'
                    });
                },
                error: function(err) {
                    console.error("Direct method test error:", err);
                    frappe.msgprint('Method call failed. Check console for error details.');
                }
            });
        }, __('Debug'));
    }
});
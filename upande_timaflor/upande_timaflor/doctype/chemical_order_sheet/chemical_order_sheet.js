// Copyright (c) 2025, newton@upande.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Chemical Order Sheet', {
    refresh: function(frm) {
        // Add a button to add all chemicals from Chemical item group
        frm.add_custom_button(__('Add All Chemicals'), function() {
            // Confirm farm areas are specified
            if (!frm.doc.farm_area_to_spray || frm.doc.farm_area_to_spray.length === 0) {
                frappe.msgprint(__('Please add at least one farm area before adding chemicals.'));
                return;
            }
            
            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.get_all_chemicals',
                freeze: true,
                freeze_message: __('Fetching chemicals...'),
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        // Clear existing spray details if user confirms
                        frappe.confirm(
                            __('This will replace your current chemicals list. Continue?'),
                            function() {
                                // Clear the existing spray details
                                frm.clear_table('spray_details');
                                
                                r.message.forEach(function(item) {
                                    let row = frm.add_child('spray_details');
                                    row.chemical = item.name;
                                    row.application_rate_per_hectare = 1; 
                                    row.required_number_of_sprays = 1;    
                                    row.number_of_sprays = 1;            
                                });
                                
                                frm.refresh_field('spray_details');
                                frappe.show_alert(__('Added ' + r.message.length + ' chemicals to the list'));
                                
                                setTimeout(function() {
                                    frm.trigger('calculate_orders');
                                }, 500);
                            }
                        );
                    } else {
                        frappe.msgprint(__('No chemicals found in the system.'));
                    }
                }
            });
        });
        
        //Button to calculate order quantities
        frm.add_custom_button(__('Calculate Order Quantities'), function() {
            // First, validate if there are farm areas and chemicals defined
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
    },
    
    validate: function(frm) {
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders');
        frm.calculate_without_popup = false;
    },
    
    calculate_orders: function(frm) {
        if (frm.doc.farm_area_to_spray && frm.doc.farm_area_to_spray.length > 0 &&
            frm.doc.spray_details && frm.doc.spray_details.length > 0) {
            
            if (!frm.calculate_without_popup) {
                frappe.show_progress(__('Calculating Orders'), 0, 100);
            }
            
            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.chemical_order_sheet.chemical_order_sheet.calculate_order_quantities',
                args: {
                    doc: frm.doc
                },
                freeze: !frm.calculate_without_popup, 
                freeze_message: __('Calculating order quantities...'),
                callback: function(r) {
                    if (!frm.calculate_without_popup) {
                        frappe.hide_progress();
                    }
                    
                    if (r.message) {
                        frm.clear_table('order_detail');
                        
                        r.message.forEach(order => {
                            let row = frm.add_child('order_detail');
                            Object.keys(order).forEach(key => {
                                row[key] = order[key];
                            });
                        });
                        
                        frm.refresh_field('order_detail');
                        frm.trigger('calculate_totals');
                        
                        if (!frm.calculate_without_popup) {
                            frappe.show_alert(__('Order quantities calculated'));
                        }
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
        // Calculate total order amount based on chemical quantities
        let total = 0;
        
        if (frm.doc.order_detail && frm.doc.order_detail.length > 0) {
            // Create a promise array for all async calls
            let promises = [];
            
            frm.doc.order_detail.forEach(function(item) {
                let total_quantity = (
                    parseFloat(item.tima_1 || 0) + 
                    parseFloat(item.tima_2 || 0) + 
                    parseFloat(item.tima_3 || 0) + 
                    parseFloat(item.tima_4 || 0) + 
                    parseFloat(item.tima_5 || 0) + 
                    parseFloat(item.tima_6 || 0) + 
                    parseFloat(item.tima_7 || 0) + 
                    parseFloat(item.jangwani || 0)
                );
                
                // Only proceed if there's a quantity to calculate
                if (total_quantity > 0 && item.item) {
                    // Create a promise for each async call
                    let promise = new Promise((resolve) => {
                        frappe.call({
                            method: 'frappe.client.get_value',
                            args: {
                                doctype: 'Item',
                                filters: { name: item.item },
                                fieldname: 'valuation_rate'
                            },
                            callback: function(r) {
                                if (r.message && r.message.valuation_rate) {
                                    let item_total = total_quantity * r.message.valuation_rate;
                                    resolve(item_total);
                                } else {
                                    resolve(0);
                                }
                            }
                        });
                    });
                    
                    promises.push(promise);
                }
            });
            
            Promise.all(promises).then(values => {
                total = values.reduce((sum, value) => sum + value, 0);
                
                if (frm.fields_dict['total_order_amount']) {
                    frm.set_value('total_order_amount', total);
                } else {
                    frm.doc.total_order_amount = total;
                    console.warn("Field 'total_order_amount' not found in the form schema. Value calculated but not displayed.");
                }
            });
        } else {
            if (frm.fields_dict['total_order_amount']) {
                frm.set_value('total_order_amount', 0);
            } else {
                frm.doc.total_order_amount = 0;
            }
        }
    }
});

frappe.ui.form.on('Area To Spray', {
    farm_area_to_spray_add: function(frm, cdt, cdn) {
        // Initialize default values for new row
        let row = locals[cdt][cdn];
        row.tima_1 = 0;
        row.tima_2 = 0;
        row.tima_3 = 0;
        row.tima_4 = 0;
        row.tima_5 = 0;
        row.tima_6 = 0;
        row.tima_7 = 0;
        row.jangwani = 0;
        frm.refresh_field('farm_area_to_spray');
    },
    
    tima_1: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    },
    tima_2: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    },
    tima_3: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    },
    tima_4: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    },
    tima_5: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    },
    tima_6: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    },
    tima_7: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    },
    jangwani: function(frm, cdt, cdn) { 
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders'); 
        frm.calculate_without_popup = false;
    }
});

frappe.ui.form.on('Chemical Sprays', {
    spray_details_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        row.application_rate_per_hectare = 1; 
        row.required_number_of_sprays = 1;    
        row.number_of_sprays = 1;             
        frm.refresh_field('spray_details');
    },
    
    chemical: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Fetch application rate when chemical changes
        if (row.chemical) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Item',
                    filters: { name: row.chemical },
                    fieldname: ['application_rate', 'default_sprays']
                },
                callback: function(r) {
                    if (r.message) {
                        if (r.message.application_rate) {
                            frappe.model.set_value(cdt, cdn, 'application_rate_per_hectare', r.message.application_rate);
                        }
                        
                        if (r.message.default_sprays) {
                            frappe.model.set_value(cdt, cdn, 'required_number_of_sprays', r.message.default_sprays);
                            frappe.model.set_value(cdt, cdn, 'number_of_sprays', r.message.default_sprays);
                        }
                        
                        // Trigger calculation after values are set
                        frm.calculate_without_popup = true;
                        frm.trigger('calculate_orders');
                        frm.calculate_without_popup = false;
                    }
                }
            });
        }
    },
    
    required_number_of_sprays: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // When required sprays change, update number of sprays if it's less than required
        if (row.number_of_sprays < row.required_number_of_sprays) {
            frappe.model.set_value(cdt, cdn, 'number_of_sprays', row.required_number_of_sprays);
        }
        
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders');
        frm.calculate_without_popup = false;
    },
    
    number_of_sprays: function(frm, cdt, cdn) {
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders');
        frm.calculate_without_popup = false;
    },
    
    application_rate_per_hectare: function(frm, cdt, cdn) {
        frm.calculate_without_popup = true;
        frm.trigger('calculate_orders');
        frm.calculate_without_popup = false;
    }
});
//Ordering sheet 
frappe.ui.form.on('Ordering Sheet', {
    refresh: function(frm) {
        // PO Creation Button 
        frm.add_custom_button(__('Create Purchase Order'), function() {
            // Check document status first
            if (frm.doc.docstatus === 0) {
                frappe.confirm(__('Document needs to be submitted before creating Purchase Order. Submit now?'), () => {
                    frm.savesubmit()
                        .then(() => {
                            if(!frm.doc.supplier) {
                                show_supplier_dialog(frm);
                            } else {
                                create_po(frm);
                            }
                        })
                        .catch((err) => {
                            frappe.msgprint(__("Error submitting document: " + (err.message || err)));
                        });
                });
            } else if (frm.doc.docstatus === 1) {
                // Document is already submitted
                if(!frm.doc.supplier) {
                    show_supplier_dialog(frm);
                } else {
                    create_po(frm);
                }
            } else {
                frappe.msgprint(__("Cannot create Purchase Order from a cancelled document"));
            }
        }, __('Create'));

        // Calculate Order Quantities Button
        frm.add_custom_button(__('Calculate Order Quantities'), function() {
            calculate_order_quantities(frm);
        });

        // Create RFQ Button
        frm.add_custom_button(__('Create RFQ'), function() {
            create_rfq(frm);
        }, __('Create'));
    },

    before_save: function(frm) {
        console.log("Trigger: before_save");

        if (frm.doc.daily_average_consumptiondays > 999) {
            frappe.msgprint(__("Daily Average Consumption Days must be less than 1000"));
            frappe.validated = false;
            return;
        }

        let item_codes = frm.doc.table_bvnr?.map(row => row.item) || [];
        
        if (item_codes.length > 0) {
            fetch_consumption_data(frm, item_codes).then(() => {
                frm.refresh_field("table_bvnr");
                frm.refresh_field("daily_minimum_consumption");
                frm.refresh_field("daily_maximum_consumption");
            }).catch(err => {
                console.error("Error fetching consumption data:", err);
                frappe.msgprint(__("Error fetching consumption data. Please check console for details."));
            });
        }
    }
});

function fetch_consumption_data(frm, item_codes) {
    if (!item_codes || item_codes.length === 0) {
        console.log("No item codes to process");
        return Promise.resolve();
    }

    console.log("Fetching consumption data for items:", item_codes);

    const from_date = frappe.datetime.add_days(frappe.datetime.nowdate(), -frm.doc.daily_average_consumptiondays);
    const to_date = frappe.datetime.nowdate();

    console.log("Date range:", from_date, "to", to_date);

    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'upande_timaflor.upande_timaflor.doctype.ordering_sheet.ordering_sheet.get_all_consumption_data',
            args: {
                item_codes: item_codes,
                from_date: from_date,
                to_date: to_date
            },
            callback: function(r) {
                if (r.exc) {
                    console.error("Error in frappe.call:", r.exc);
                    reject(r.exc);
                    return;
                }

                if (r.message) {
                    console.log("Consumption data received:", r.message);

                    process_consumption_data(frm, r.message.average, "table_bvnr", "avg");
                    process_consumption_data(frm, r.message.minimum, "daily_minimum_consumption", "minimum");
                    process_consumption_data(frm, r.message.maximum, "daily_maximum_consumption", "maximum");

                    resolve();
                } else {
                    console.log("No data returned");
                    resolve();
                }
            }
        });
    });
}

function process_consumption_data(frm, data, table_field, data_type) {
    if (!data) {
        console.log(`No ${data_type} data provided`);
        return;
    }

    if (!frm.doc[table_field]) {
        console.log(`Initializing ${table_field} table`);
        frm.doc[table_field] = [];
    }

    console.log(`Processing ${data_type} data for ${table_field}`, data);

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

    frm.doc[table_field] = [];

    Object.entries(data).forEach(([item_code, farm_data]) => {
        console.log(`Adding ${item_code} to ${table_field}`);
        const row = frappe.model.add_child(frm.doc, table_field.charAt(0).toUpperCase() + table_field.slice(1), table_field);
        row.item = item_code;

        Object.values(fieldMap[data_type]).forEach(field => {
            row[field] = 0;
        });

        Object.entries(farm_data).forEach(([farm, value]) => {
            const field = fieldMap[data_type][farm];
            if (field) {
                const safeValue = parseFloat(value) || 0;
                row[field] = isNaN(safeValue) || !isFinite(safeValue) ? 0 : safeValue;
            }
        });
    });

    frm.refresh_field(table_field);
}

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
        }).catch(err => {
            frappe.msgprint(`Error creating Purchase Order: ${err.message || err}`);
        });
    });
}

function create_rfq(frm) {
    if (frm.is_dirty()) {
        // Save the document first if there are unsaved changes
        frm.save().then(() => {
            proceedWithRFQCreation(frm);
        }).catch((err) => {
            frappe.msgprint(__("Error saving document. Please try again."));
        });
    } else {
        proceedWithRFQCreation(frm);
    }
}

function proceedWithRFQCreation(frm) {
    if (!frm.doc.order_quantity || frm.doc.order_quantity.length === 0) {
        frappe.msgprint(__('No order quantities available - please calculate order quantities first'));
        return;
    }

    // First check if document is in draft state
    if (frm.doc.docstatus === 0) {
        // Save and submit document first
        frappe.confirm(__('Document needs to be submitted before creating RFQ. Submit now?'), () => {
            frm.savesubmit()
                .then(() => {
                    createRFQFromSubmittedDoc(frm);
                })
                .catch((err) => {
                    frappe.msgprint(__("Error submitting document: " + (err.message || err)));
                });
        });
    } else if (frm.doc.docstatus === 1) {
        // Document is already submitted, proceed with RFQ creation
        createRFQFromSubmittedDoc(frm);
    } else {
        frappe.msgprint(__("Cannot create RFQ from a cancelled document"));
    }
}

function createRFQFromSubmittedDoc(frm) {
    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.ordering_sheet.ordering_sheet.create_rfq',
        args: {
            ordering_sheet: frm.doc.name
        },
        callback: function(r) {
            if (r.exc) {
                frappe.msgprint(`Error creating RFQ: ${r.exc}`);
                return;
            }
            if (r.message) {
                frappe.show_alert({
                    message: __('RFQ created: ' + r.message),
                    indicator: 'green'
                });
                frappe.set_route('Form', 'Request for Quotation', r.message);
            }
        }
    });
}

function calculate_order_quantities(frm) {
    if (!frm.doc.ordering_quantity) {
        frappe.throw(__('Please set an Ordering Quantity first'));
        return;
    }

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
            
            // Check if the document is in submitted state
            const wasSubmitted = frm.doc.docstatus === 1;
            
            // If document is already submitted, we'll update via server method
            if (wasSubmitted) {
                update_order_quantities_server(frm, values.calculation_base);
                return;
            }
            
            // For draft documents, continue with client-side update
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
                    show_custom_values_dialog(frm);
                    return;
            }

            if (source_table && source_table.length > 0) {
                source_table.forEach(source_row => {
                    let order_row = frappe.model.add_child(frm.doc, "Order Quantity", "order_quantity");
                    order_row.item = source_row.item;

                    Object.entries(field_map).forEach(([source_field, target_field]) => {
                        const baseValue = source_row[source_field] || 0;
                        const calculatedValue = baseValue * frm.doc.ordering_quantity;
                        order_row[target_field] = isNaN(calculatedValue) || !isFinite(calculatedValue) ? 0 : calculatedValue;
                    });
                });

                frm.refresh_field("order_quantity");
                
                // Save without submit
                frm.save().then(() => {
                    frappe.show_alert({
                        message: __('Order quantities calculated and saved based on ' + values.calculation_base),
                        indicator: 'green'
                    });
                }).catch(err => {
                    frappe.msgprint(__("Error saving calculated quantities: " + (err.message || err)));
                });
            } else {
                frappe.msgprint(__('No source data found for ' + values.calculation_base));
            }
        }
    });
    dialog.show();
}

// New function to update order quantities via server method for submitted documents
function update_order_quantities_server(frm, calculation_base) {
    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.ordering_sheet.ordering_sheet.update_order_quantities',
        args: {
            doc_name: frm.doc.name,
            calculation_base: calculation_base,
            ordering_quantity: frm.doc.ordering_quantity
        },
        freeze: true,
        freeze_message: __('Calculating Order Quantities...'),
        callback: function(r) {
            if (r.exc) {
                frappe.msgprint(__("Error calculating order quantities: " + r.exc));
                return;
            }
            
            if (r.message) {
                // Reload the form to get the updated data
                frm.reload_doc();
                
                frappe.show_alert({
                    message: __('Order quantities calculated based on ' + calculation_base),
                    indicator: 'green'
                });
            }
        }
    });
}

function show_custom_values_dialog(frm) {
    let items = [];

    if (frm.doc.table_bvnr && frm.doc.table_bvnr.length > 0) {
        items = frm.doc.table_bvnr.map(row => ({ label: row.item, value: row.item }));
    } else if (frm.doc.daily_minimum_consumption && frm.doc.daily_minimum_consumption.length > 0) {
        items = frm.doc.daily_minimum_consumption.map(row => ({ label: row.item, value: row.item }));
    } else if (frm.doc.daily_maximum_consumption && frm.doc.daily_maximum_consumption.length > 0) {
        items = frm.doc.daily_maximum_consumption.map(row => ({ label: row.item, value: row.item }));
    }

    if (items.length === 0) {
        frappe.msgprint(__('No items found for custom order calculation'));
        return;
    }

    const dialog = new frappe.ui.Dialog({
        title: __('Enter Custom Order Values'),
        fields: [
            { label: __('Item'), fieldname: 'item', fieldtype: 'Select', options: items, reqd: 1 },
            { label: __('TIMA 1'), fieldname: 'tima_1', fieldtype: 'Float', default: 0 },
            { label: __('TIMA 2'), fieldname: 'tima_2', fieldtype: 'Float', default: 0 },
            { label: __('TIMA 3'), fieldname: 'tima_3', fieldtype: 'Float', default: 0 },
            { label: __('TIMA 4'), fieldname: 'tima_4', fieldtype: 'Float', default: 0 },
            { label: __('TIMA 5'), fieldname: 'tima_5', fieldtype: 'Float', default: 0 },
            { label: __('TIMA 6'), fieldname: 'tima_6', fieldtype: 'Float', default: 0 },
            { label: __('TIMA 7'), fieldname: 'tima_7', fieldtype: 'Float', default: 0 },
            { label: __('Jangwani'), fieldname: 'jangwani', fieldtype: 'Float', default: 0 }
        ],
        primary_action: function(values) {
            const wasSubmitted = frm.doc.docstatus === 1;
            
            if (wasSubmitted) {
                // For submitted documents, use server method
                frappe.call({
                    method: 'upande_timaflor.upande_timaflor.doctype.ordering_sheet.ordering_sheet.add_custom_order_quantity',
                    args: {
                        doc_name: frm.doc.name,
                        item_values: values
                    },
                    callback: function(r) {
                        if (r.exc) {
                            frappe.msgprint(__("Error adding custom order: " + r.exc));
                            return;
                        }
                        
                        dialog.hide();
                        frm.reload_doc();
                        
                        frappe.show_alert({
                            message: __('Custom order added successfully'),
                            indicator: 'green'
                        });
                    }
                });
            } else {
                // For draft documents
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

                dialog.fields_dict.tima_1.set_value(0);
                dialog.fields_dict.tima_2.set_value(0);
                dialog.fields_dict.tima_3.set_value(0);
                dialog.fields_dict.tima_4.set_value(0);
                dialog.fields_dict.tima_5.set_value(0);
                dialog.fields_dict.tima_6.set_value(0);
                dialog.fields_dict.tima_7.set_value(0);
                dialog.fields_dict.jangwani.set_value(0);

                frappe.show_alert({
                    message: __('Item added to Order Quantity'),
                    indicator: 'green'
                });
            }
        }
    });

    dialog.show();
}
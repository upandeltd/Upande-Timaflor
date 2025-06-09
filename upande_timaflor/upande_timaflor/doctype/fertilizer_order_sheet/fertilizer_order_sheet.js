frappe.ui.form.on('Fertilizer Order Sheet', {
    refresh: function(frm) {
        // Add custom buttons
        frm.add_custom_button(__('Calculate & Populate Averages'), function() {
            calculate_and_populate_averages(frm);
        }).addClass('btn-primary');

        frm.add_custom_button(__('Refresh Stock Levels'), function() {
            refresh_stock_levels(frm);
        }).addClass('btn-primary');

        frm.add_custom_button(__('Calculate Order Quantities'), function() {
            calculate_order_quantities(frm);
        }).addClass('btn-info');

        frm.add_custom_button(__('Clean Up Data'), function() {
            cleanup_consumption_data(frm);
        }).addClass('btn-warning');

        // Debug buttons
        //frm.add_custom_button(__('Debug Data'), function() {debug_fertilizer_data(frm); }, __('Debug'));

        //frm.add_custom_button(__('Validate Setup'), function() {validate_setup(frm); }, __('Debug'));

        //frm.add_custom_button(__('Debug Consumption'), function() {debug_consumption_table(frm);}, __('Debug'));
        frm.add_custom_button(__('Create RFQ'), function() {
            create_request_for_quotation(frm);
        }, __('Create'));

        frm.add_custom_button(__('Create PO'), function() {
            create_purchase_order(frm);
        }, __('Create'));
    },
    

    average_consumption: function(frm) {
        update_consumption_for_all_rows(frm);
    },

    stock_wanted_weeks: function(frm) {
        update_stock_wanted_for_all_rows(frm);
    }
});

function create_request_for_quotation(frm) {
    if (!frm.doc.order_quantity || frm.doc.order_quantity.length === 0) {
        frappe.msgprint(__('Please calculate order quantities first.'));
        return;
    }

    let items_to_order = [];

    frm.doc.order_quantity.forEach(item => {
        if (item.calculated_order_quantity > 0) {
            items_to_order.push({
                item_code: item.item,
                item_name: item.item_name || item.item,
                qty: item.calculated_order_quantity,
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
        rfq.fertilizer_order_sheet = frm.doc.name;

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

function create_purchase_order(frm) {
    if (!frm.doc.order_quantity || frm.doc.order_quantity.length === 0) {
        frappe.msgprint(__('Please calculate order quantities first.'));
        return;
    }

    let items_to_order = [];

    frm.doc.order_quantity.forEach(item => {
        if (item.calculated_order_quantity > 0) {
            items_to_order.push({
                item_code: item.item,
                item_name: item.item_name || item.item,
                qty: item.calculated_order_quantity,
                schedule_date: frappe.datetime.add_days(frappe.datetime.nowdate(), 7)
            });
        }
    });

    if (items_to_order.length === 0) {
        frappe.msgprint(__('No items with quantities to order.'));
        return;
    }

    let d = new frappe.ui.Dialog({
        title: __('Create Purchase Order'),
        fields: [
            {
                label: __('Supplier'),
                fieldname: 'supplier',
                fieldtype: 'Link',
                options: 'Supplier',
                reqd: 1
            },
            {
                label: __('Submit PO'),
                fieldname: 'submit_po',
                fieldtype: 'Check',
                default: 0,
                description: __('Submit the purchase order immediately after creation')
            }
        ],
        primary_action_label: __('Create'),
        primary_action(values) {
            create_po_with_items(frm, items_to_order, values.supplier, values.submit_po);
            d.hide();
        }
    });
    d.show();
}

function create_po_with_items(frm, items_to_order, supplier, submit_po = false) {
    frappe.model.with_doctype('Purchase Order', function() {
        let po = frappe.model.get_new_doc('Purchase Order');
        po.supplier = supplier;
        po.transaction_date = frappe.datetime.nowdate();
        po.fertilizer_order_sheet = frm.doc.name;

        items_to_order.forEach(item => {
            let po_item = frappe.model.add_child(po, 'items');
            po_item.item_code = item.item_code;
            po_item.item_name = item.item_name;
            po_item.qty = item.qty;
            po_item.schedule_date = item.schedule_date;
        });

        frappe.set_route('Form', po.doctype, po.name);
        
        if (submit_po) {
            frappe.call({
                method: 'frappe.client.save',
                args: {
                    doc: po
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.model.sync();
                        frappe.call({
                            method: 'frappe.client.submit',
                            args: {
                                doctype: 'Purchase Order',
                                name: r.message.name
                            },
                            callback: function() {
                                frappe.show_alert({
                                    message: __('Purchase Order submitted successfully'),
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        });
                    }
                }
            });
        }
    });
}

function validate_setup(frm) {
    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.validate_fertilizer_setup',
        callback: function(r) {
            if (r.message && !r.message.error) {
                frappe.msgprint({
                    title: __('Setup Validation'),
                    message: `
                        <strong>Warehouses:</strong><br>
                        ✓ Found: ${r.message.existing_warehouses.length}<br>
                        ✗ Missing: ${r.message.missing_warehouses.length}<br>
                        <strong>Fertilizer Items:</strong> ${r.message.fertilizer_items_count}<br><br>
                        ${r.message.missing_warehouses.length > 0 ? 
                            '<strong>Missing Warehouses:</strong><br>' + 
                            r.message.missing_warehouses.join('<br>') : 
                            'All warehouses found!'}
                    `,
                    indicator: r.message.missing_warehouses.length > 0 ? 'orange' : 'green'
                });
            }
        }
    });
}

async function cleanup_consumption_data(frm) {
    if (!frm.doc.weekly_average_consumption || frm.doc.weekly_average_consumption.length === 0) {
        frappe.msgprint(__('No data to clean up.'));
        return;
    }

    let valid_rows = [];
    let removed_count = 0;

    // Filter out invalid rows (only check for item)
    for (const row of frm.doc.weekly_average_consumption) {
        if (row.item && row.item.trim() !== '') {
            valid_rows.push({
                item: row.item,
                average_consumption: row.average_consumption || 0,
                stock_wanted_weeks: row.stock_wanted_weeks || 0
            });
        } else {
            removed_count++;
        }
    }

    // Update the table with valid rows
    frm.clear_table('weekly_average_consumption');
    for (const row of valid_rows) {
        let new_row = frm.add_child('weekly_average_consumption');
        frappe.model.set_value(new_row.doctype, new_row.name, 'item', row.item);
        frappe.model.set_value(new_row.doctype, new_row.name, 'average_consumption', row.average_consumption);
        frappe.model.set_value(new_row.doctype, new_row.name, 'stock_wanted_weeks', row.stock_wanted_weeks);
    }
    frm.refresh_field('weekly_average_consumption');
    if (valid_rows.length > 0) {
        frm.save().then(() => {
            frappe.show_alert({
                message: __('Cleaned up data: {0} invalid rows removed').replace('{0}', removed_count),
                indicator: 'green'
            }, 5);
        });
    } else {
        frappe.msgprint(__('No valid rows found after cleanup.'));
    }
}

function debug_consumption_table(frm) {
    console.log('=== CONSUMPTION TABLE DEBUG ===');
    
    if (!frm.doc.weekly_average_consumption || frm.doc.weekly_average_consumption.length === 0) {
        frappe.msgprint('No consumption data found');
        return;
    }
    
    let valid_rows = 0;
    let invalid_rows = 0;
    let missing_item_name = 0;
    let missing_item_code = 0;
    
    frm.doc.weekly_average_consumption.forEach((row, idx) => {
        let has_item = row.item && row.item.trim() !== '';
        let has_item_name = row.item_name && row.item_name.trim() !== '';
        
        if (!has_item) missing_item_code++;
        if (!has_item_name) missing_item_name++;
        
        if (has_item && has_item_name) {
            valid_rows++;
        } else {
            invalid_rows++;
        }
        
        console.log(`Row ${idx + 1}:`, {
            item: `"${row.item || ''}"`,
            item_name: `"${row.item_name || ''}"`,
            has_item: has_item,
            has_item_name: has_item_name,
            avg_consumption: row.average_consumption,
            stock_wanted_weeks: row.stock_wanted_weeks,
            valid: has_item && has_item_name
        });
    });
    
    frappe.msgprint({
        title: 'Consumption Table Debug',
        message: `
            <strong>Total Rows:</strong> ${frm.doc.weekly_average_consumption.length}<br>
            <strong>Valid Rows:</strong> ${valid_rows}<br>
            <strong>Invalid Rows:</strong> ${invalid_rows}<br>
            <strong>Missing Item Code:</strong> ${missing_item_code}<br>
            <strong>Missing Item Name:</strong> ${missing_item_name}<br><br>
            Check console for detailed row information.
        `,
        indicator: invalid_rows > 0 ? 'red' : 'green'
    });
}

function debug_fertilizer_data(frm) {
    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.debug_fertilizer_data',
        callback: function(r) {
            if (r.message && !r.message.error) {
                console.log('=== FERTILIZER DEBUG DATA ===');
                console.log('Items:', r.message.items);
                console.log('Stock Entries:', r.message.stock);
                console.log('Warehouses:', r.message.warehouses);
                
                frappe.msgprint({
                    title: __('Debug Data'),
                    message: `
                        <strong>Items Found:</strong> ${r.message.items_count}<br>
                        <strong>Stock Entries:</strong> ${r.message.stock_entries}<br>
                        <strong>Warehouses:</strong> ${r.message.warehouses.length}<br><br>
                        Check console for detailed data.
                    `,
                    indicator: 'blue'
                });
            }
        }
    });
}

function calculate_and_populate_averages(frm) {
    if (!frm.doc.name) {
        frappe.msgprint(__('Please save the document first.'));
        return;
    }

    if (!frm.doc.average_consumption || frm.doc.average_consumption <= 0) {
        frappe.msgprint(__('Please enter a valid number of weeks for average calculation.'));
        return;
    }

    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.calculate_historical_consumption',
        args: {
            weeks_to_calculate: frm.doc.average_consumption
        },
        freeze: true,
        freeze_message: __('Calculating historical consumption...'),
        callback: function(r) {
            if (r.message && !r.message.error) {
                let data = r.message;
                if (!data || data.length === 0) {
                    frappe.msgprint({ message: __('No fertilizer items found or no consumption data for the selected period.'), indicator: 'orange' });
                    return;
                }

                // Clear the table to ensure a fresh list
                frm.clear_table('weekly_average_consumption');

                let stock_wanted_weeks = frm.doc.stock_wanted_weeks || 0;

                data.sort((a, b) => a.item_name.localeCompare(b.item_name)).forEach(item => {
                    let row = frm.add_child('weekly_average_consumption');
                    // Ensure both item and item_name are set
                    row.item = item.item_code;
                    row.item_name = item.item_name || item.item_code;  // Fallback to item_code if item_name is missing
                    row.average_consumption = item.average_consumption;
                    row.stock_wanted_weeks = stock_wanted_weeks > 0 ? stock_wanted_weeks : 0;
                });

                frm.refresh_field('weekly_average_consumption');
                frm.save().then(() => {
                    frappe.show_alert({
                        message: __('Successfully calculated and populated averages for {0} items.', [data.length]),
                        indicator: 'green'
                    }, 7);
                });

            } else {
                frappe.msgprint({
                    title: __('Error'),
                    indicator: 'red',
                    message: r.message?.error || __('An unknown error occurred during calculation.')
                });
            }
        }
    });
}

function refresh_stock_levels(frm) {
    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.get_warehouse_specific_stock',
        freeze: true,
        freeze_message: __('Fetching stock levels...'),
        callback: function(r) {
            if (r.message && !r.message.error) {
                update_stock_table(frm, r.message);
            } else {
                handle_stock_error(r);
            }
        }
    });
}

function add_all_fertilizers(frm) {
    // Validate required fields
    let avg_consumption = parseFloat(frm.doc.average_consumption) || 0;
    let stock_wanted_weeks = parseFloat(frm.doc.stock_wanted_weeks) || 0;
    
    if (!avg_consumption || avg_consumption <= 0) {
        frappe.msgprint({
            title: __('Missing Data'),
            indicator: 'orange',
            message: __('Please set Average Consumption value first (must be > 0). Current value: ') + frm.doc.average_consumption
        });
        return;
    }
    
    if (!stock_wanted_weeks || stock_wanted_weeks <= 0) {
        frappe.msgprint({
            title: __('Missing Data'),
            indicator: 'orange',
            message: __('Please set Stock Wanted(Weeks) value first (must be > 0). Current value: ') + frm.doc.stock_wanted_weeks
        });
        return;
    }

    frappe.call({
        method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.get_all_fertilizers',
        freeze: true,
        freeze_message: __('Adding all fertilizers...'),
        callback: function(r) {
            if (r.message && !r.message.error) {
                frm.clear_table('weekly_average_consumption');
                let sorted_fertilizers = r.message.sort((a, b) => a.item_name.localeCompare(b.item_name));
                
                console.log('Adding fertilizers:', {
                    avg_consumption: avg_consumption,
                    stock_wanted_weeks: stock_wanted_weeks,
                    items_count: sorted_fertilizers.length
                });
                
                sorted_fertilizers.forEach((item) => {
                    let row = frm.add_child('weekly_average_consumption');
                    // FIXED: Proper mapping of item code and item name
                    frappe.model.set_value(row.doctype, row.name, 'item', item.item_code);  // Item code
                    frappe.model.set_value(row.doctype, row.name, 'item_name', item.item_name);  // Item name
                    frappe.model.set_value(row.doctype, row.name, 'average_consumption', avg_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'stock_wanted_weeks', stock_wanted_weeks);
                });

                frm.refresh_field('weekly_average_consumption');
                frm.save().then(() => {
                    frappe.show_alert({
                        message: __('Added {0} fertilizers to consumption table').replace('{0}', sorted_fertilizers.length),
                        indicator: 'green'
                    }, 5);
                });
                
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    indicator: 'red',
                    message: __('Error adding fertilizers: ') + (r.message?.error || 'Unknown error')
                });
            }
        }
    });
}

function update_consumption_for_all_rows(frm) {
    if (!frm.doc.weekly_average_consumption || frm.doc.weekly_average_consumption.length === 0) return;
    
    let avg_consumption = parseFloat(frm.doc.average_consumption) || 0;
    if (avg_consumption > 0) {
        let updated = false;
        frm.doc.weekly_average_consumption.forEach(row => {
            if (row.item && row.item_name) {  // Only update valid rows
                frappe.model.set_value(row.doctype, row.name, 'average_consumption', avg_consumption);
                updated = true;
            }
        });
        
        if (updated) {
            frm.refresh_field('weekly_average_consumption');
            frm.save();
        }
    }
}

function update_stock_wanted_for_all_rows(frm) {
    if (!frm.doc.weekly_average_consumption || frm.doc.weekly_average_consumption.length === 0) return;
    
    let stock_wanted_weeks = parseFloat(frm.doc.stock_wanted_weeks) || 0;
    if (stock_wanted_weeks > 0) {
        let updated = false;
        frm.doc.weekly_average_consumption.forEach(row => {
            if (row.item && row.item_name) {  // Only update valid rows
                frappe.model.set_value(row.doctype, row.name, 'stock_wanted_weeks', stock_wanted_weeks);
                updated = true;
            }
        });
        
        if (updated) {
            frm.refresh_field('weekly_average_consumption');
            frm.save();
        }
    }
}

function calculate_order_quantities(frm) {
    // Validate data before calculation
    let consumption_data = frm.doc.weekly_average_consumption || [];
    let stock_data = frm.doc.stock_levels || [];

    if (consumption_data.length === 0) {
        frappe.msgprint({
            title: __('No Data'),
            indicator: 'orange',
            message: __('Please add fertilizers to the consumption table first using "Add All Fertilizers" button.')
        });
        return;
    }

    if (stock_data.length === 0) {
        frappe.msgprint({
            title: __('No Stock Data'),
            indicator: 'orange',
            message: __('Please refresh stock levels first using "Refresh Stock Levels" button.')
        });
        return;
    }

    // Check for invalid rows
    let invalid_rows = frm.doc.weekly_average_consumption.filter(row => !row.item || row.item.trim() === '');
    if (invalid_rows.length > 0) {
        frappe.msgprint(__(`Found ${invalid_rows.length} rows with missing item codes. Please use 'Clean Up Data' button to fix this.`));
        return;
    }

    // Create stock lookup map
    let stock_map = {};
    stock_data.forEach(stock => {
        stock_map[stock.item] = {
            tima_1: flt(stock.tima_1) || 0,
            tima_2: flt(stock.tima_2) || 0,
            tima_3: flt(stock.tima_3) || 0,
            tima_4: flt(stock.tima_4) || 0,
            tima_5: flt(stock.tima_5) || 0,
            tima_6: flt(stock.tima_6) || 0,
            tima_7: flt(stock.tima_7) || 0,
            jangwani: flt(stock.jangwani) || 0
        };
    });

    // Clear and populate order quantity table
    frm.clear_table('order_quantity');
    let calculated_count = 0;
    let skipped_count = 0;

    // Filter and sort valid consumption data
    let valid_consumption = consumption_data.filter(row => 
        row.item && row.item_name && 
        row.item.trim() !== '' && row.item_name.trim() !== ''
    );

    valid_consumption.sort((a, b) => a.item_name.localeCompare(b.item_name)).forEach(consumption => {
        let row_avg_consumption = flt(consumption.average_consumption) || 0;
        let row_stock_wanted_weeks = flt(consumption.stock_wanted_weeks) || 0;
        
        // Use row values if available, otherwise use main form values
        let avg_consumption = row_avg_consumption > 0 ? row_avg_consumption : flt(frm.doc.average_consumption) || 0;
        let stock_wanted_weeks = row_stock_wanted_weeks > 0 ? row_stock_wanted_weeks : flt(frm.doc.stock_wanted_weeks) || 0;

        if (avg_consumption > 0 && stock_wanted_weeks > 0) {
            let current_stock = stock_map[consumption.item] || {
                tima_1: 0, tima_2: 0, tima_3: 0, tima_4: 0,
                tima_5: 0, tima_6: 0, tima_7: 0, jangwani: 0
            };
            
            // Calculate required stock and order quantity for each farm
            let required_stock = avg_consumption * stock_wanted_weeks;
            
            // Add to order quantity table
            let order_row = frm.add_child('order_quantity', {
                item: consumption.item,
                item_name: consumption.item_name,
                tima_1: Math.ceil(Math.max(0, required_stock - current_stock.tima_1)),
                tima_2: Math.ceil(Math.max(0, required_stock - current_stock.tima_2)),
                tima_3: Math.ceil(Math.max(0, required_stock - current_stock.tima_3)),
                tima_4: Math.ceil(Math.max(0, required_stock - current_stock.tima_4)),
                tima_5: Math.ceil(Math.max(0, required_stock - current_stock.tima_5)),
                tima_6: Math.ceil(Math.max(0, required_stock - current_stock.tima_6)),
                tima_7: Math.ceil(Math.max(0, required_stock - current_stock.tima_7)),
                jangwani: Math.ceil(Math.max(0, required_stock - current_stock.jangwani))
            });
            
            calculated_count++;
        } else {
            skipped_count++;
        }
    });

    frm.refresh_field('order_quantity');
    
    if (calculated_count > 0) {
        frm.save().then(() => {
            frappe.show_alert({
                message: __('Calculated order quantities for {0} items').replace('{0}', calculated_count) + 
                        (skipped_count > 0 ? __(', skipped {0} items').replace('{0}', skipped_count) : ''),
                indicator: 'green'
            }, 5);
        });
    } else {
        frappe.msgprint(__('No items met the criteria for order calculation.'));
    }
}

function update_stock_table(frm, data) {
    frm.clear_table('stock_levels');
    
    data.sort((a, b) => a.item_name.localeCompare(b.item_name)).forEach(item => {
        frm.add_child('stock_levels', {
            item: item.item_code,  // Item code
            item_name: item.item_name,  // Item name
            item_code: item.item_code,  // Explicit item code
            tima_1: parseFloat(item.tima_1) || 0,
            tima_2: parseFloat(item.tima_2) || 0,
            tima_3: parseFloat(item.tima_3) || 0,
            tima_4: parseFloat(item.tima_4) || 0,
            tima_5: parseFloat(item.tima_5) || 0,
            tima_6: parseFloat(item.tima_6) || 0,
            tima_7: parseFloat(item.tima_7) || 0,
            jangwani: parseFloat(item.jangwani) || 0,
            total_stock: parseFloat(item.total_stock) || 0
        });
    });
    
    frm.refresh_field('stock_levels');
    frm.save().then(() => {
        frappe.show_alert({
            message: __('Stock levels updated for {0} items').replace('{0}', data.length),
            indicator: 'green'
        }, 5);
    });
}

function handle_stock_error(r) {
    let error = r.message?.error || __('Unknown error');
    console.error('Stock Error:', error);
    frappe.msgprint({
        title: __('Stock Update Failed'),
        indicator: 'red',
        message: __('Error fetching stock levels: ') + error
    });
}
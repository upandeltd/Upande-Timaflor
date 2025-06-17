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
            console.log('Calculate Order Quantities button clicked');
            calculate_order_quantities(frm);
        }).addClass('btn-info');

        frm.add_custom_button(__('Clean Up Data'), function() {
            cleanup_consumption_data(frm);
        }).addClass('btn-warning');

        // Debug buttons
        frm.add_custom_button(__('Debug Data'), function() {debug_fertilizer_data(frm); }, __('Debug'));

        frm.add_custom_button(__('Validate Setup'), function() {validate_setup(frm); }, __('Debug'));

        frm.add_custom_button(__('Debug Consumption'), function() {debug_consumption_table(frm);}, __('Debug'));
        frm.add_custom_button(__('Create RFQ'), function() {
            create_request_for_quotation(frm);
        }, __('Create'));

        frm.add_custom_button(__('Create PO'), function() {
            create_purchase_order(frm);
        }, __('Create'));
    },
    

    average_consumption: function(frm) {
        //update_consumption_for_all_rows(frm);
    },

    stock_wantedweeks: function(frm) {
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
                tima_1: row.tima_1 || 0,
                tima_2: row.tima_2 || 0,
                tima_3: row.tima_3 || 0,
                tima_4: row.tima_4 || 0,
                tima_5: row.tima_5 || 0,
                tima_6: row.tima_6 || 0,
                tima_7: row.tima_7 || 0,
                jangwani: row.jangwani || 0
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
        frappe.model.set_value(new_row.doctype, new_row.name, 'tima_1', row.tima_1);
        frappe.model.set_value(new_row.doctype, new_row.name, 'tima_2', row.tima_2);
        frappe.model.set_value(new_row.doctype, new_row.name, 'tima_3', row.tima_3);
        frappe.model.set_value(new_row.doctype, new_row.name, 'tima_4', row.tima_4);
        frappe.model.set_value(new_row.doctype, new_row.name, 'tima_5', row.tima_5);
        frappe.model.set_value(new_row.doctype, new_row.name, 'tima_6', row.tima_6);
        frappe.model.set_value(new_row.doctype, new_row.name, 'tima_7', row.tima_7);
        frappe.model.set_value(new_row.doctype, new_row.name, 'jangwani', row.jangwani);
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
    let missing_item_code = 0;
    
    frm.doc.weekly_average_consumption.forEach((row, idx) => {
        let has_item = row.item && row.item.trim() !== '';
        
        if (!has_item) missing_item_code++;
        
        if (has_item) {
            valid_rows++;
        } else {
            invalid_rows++;
        }
        
        console.log(`Row ${idx + 1}:`, {
            item: `"${row.item || ''}"`,
            tima_1: row.tima_1 || 0,
            tima_2: row.tima_2 || 0,
            tima_3: row.tima_3 || 0,
            tima_4: row.tima_4 || 0,
            tima_5: row.tima_5 || 0,
            tima_6: row.tima_6 || 0,
            tima_7: row.tima_7 || 0,
            jangwani: row.jangwani || 0,
            has_item: has_item,
            valid: has_item
        });
    });
    
    frappe.msgprint({
        title: 'Consumption Table Debug',
        message: `
            <strong>Total Rows:</strong> ${frm.doc.weekly_average_consumption.length}<br>
            <strong>Valid Rows:</strong> ${valid_rows}<br>
            <strong>Invalid Rows:</strong> ${invalid_rows}<br>
            <strong>Missing Item Code:</strong> ${missing_item_code}<br><br>
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

                data.sort((a, b) => a.item_name.localeCompare(b.item_name)).forEach(item => {
                    let row = frm.add_child('weekly_average_consumption');
                    // Set the item and farm-specific consumption values
                    row.item = item.item_code;
                    row.tima_1 = flt(item.tima_1) || 0;
                    row.tima_2 = flt(item.tima_2) || 0;
                    row.tima_3 = flt(item.tima_3) || 0;
                    row.tima_4 = flt(item.tima_4) || 0;
                    row.tima_5 = flt(item.tima_5) || 0;
                    row.tima_6 = flt(item.tima_6) || 0;
                    row.tima_7 = flt(item.tima_7) || 0;
                    row.jangwani = flt(item.jangwani) || 0;
                });

                frm.refresh_field('weekly_average_consumption');
                frm.save().then(() => {
                    frappe.show_alert({
                        message: __('Successfully calculated and populated farm-specific averages for {0} items.', [data.length]),
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
    let stock_wanted_weeks = parseFloat(frm.doc.stock_wantedweeks) || 0;
    
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
            message: __('Please set Stock Wanted(Weeks) value first (must be > 0). Current value: ') + frm.doc.stock_wantedweeks
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
                    // Set only the fields that exist in the child table
                    frappe.model.set_value(row.doctype, row.name, 'item', item.item_code);
                    // Set default consumption values for each farm (can be adjusted manually)
                    let default_consumption = flt(avg_consumption / 8, 2); // Distribute evenly across 8 farms
                    frappe.model.set_value(row.doctype, row.name, 'tima_1', default_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'tima_2', default_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'tima_3', default_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'tima_4', default_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'tima_5', default_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'tima_6', default_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'tima_7', default_consumption);
                    frappe.model.set_value(row.doctype, row.name, 'jangwani', default_consumption);
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
        let avg_per_farm = flt(avg_consumption / 8, 2); // Distribute evenly across 8 farms
        
        frm.doc.weekly_average_consumption.forEach(row => {
            if (row.item) {  // Only update valid rows
                frappe.model.set_value(row.doctype, row.name, 'tima_1', avg_per_farm);
                frappe.model.set_value(row.doctype, row.name, 'tima_2', avg_per_farm);
                frappe.model.set_value(row.doctype, row.name, 'tima_3', avg_per_farm);
                frappe.model.set_value(row.doctype, row.name, 'tima_4', avg_per_farm);
                frappe.model.set_value(row.doctype, row.name, 'tima_5', avg_per_farm);
                frappe.model.set_value(row.doctype, row.name, 'tima_6', avg_per_farm);
                frappe.model.set_value(row.doctype, row.name, 'tima_7', avg_per_farm);
                frappe.model.set_value(row.doctype, row.name, 'jangwani', avg_per_farm);
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
    console.log('update_stock_wanted_for_all_rows called - this should not happen when clicking Calculate Order Quantities');
    // This function is no longer needed since stock_wanted_weeks is not stored in the child table
    // It's stored in the main form and used for calculations
    // frappe.msgprint(__('Stock wanted weeks is set at the form level and used for order calculations.'));
}

function calculate_order_quantities(frm) {
    console.log('=== CALCULATE ORDER QUANTITIES STARTED ===');
    console.log('Form doc:', frm.doc);
    
    // Validate data before calculation
    let consumption_data = frm.doc.weekly_average_consumption || [];
    let stock_data = frm.doc.stock_levels || [];

    console.log('Consumption data length:', consumption_data.length);
    console.log('Stock data length:', stock_data.length);

    if (consumption_data.length === 0) {
        console.log('No consumption data found');
        frappe.msgprint({
            title: __('No Data'),
            indicator: 'orange',
            message: __('Please add fertilizers to the consumption table first using "Add All Fertilizers" button.')
        });
        return;
    }

    if (stock_data.length === 0) {
        console.log('No stock data found');
        frappe.msgprint({
            title: __('No Stock Data'),
            indicator: 'orange',
            message: __('Please refresh stock levels first using "Refresh Stock Levels" button.')
        });
        return;
    }

    if (stock_data.length === 0) {
        console.log('No stock data found');
        frappe.msgprint({
            title: __('No Stock Data'),
            indicator: 'orange',
            message: __('Please refresh stock levels first using "Refresh Stock Levels" button.')
        });
        return;
    }

    // Check for invalid rows
    let invalid_rows = frm.doc.weekly_average_consumption.filter(row => !row.item || row.item.trim() === '');
    console.log('Invalid rows count:', invalid_rows.length);
    
    if (invalid_rows.length > 0) {
        console.log('Found invalid rows');
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

    console.log('Stock map created:', stock_map);

    // Clear and populate order quantity table
    frm.clear_table('order_quantity');
    let calculated_count = 0;
    let skipped_count = 0;

    // Filter and sort valid consumption data
    let valid_consumption = consumption_data.filter(row => 
        row.item && row.item.trim() !== '' && row.item !== null && row.item !== undefined
    );

    console.log('Valid consumption rows:', valid_consumption.length);
    
    if (valid_consumption.length === 0) {
        console.log('No valid consumption rows found');
        frappe.msgprint({
            title: __('No Valid Data'),
            indicator: 'orange',
            message: __('No valid consumption data found. Please ensure all rows have valid item codes.')
        });
        return;
    }

    // Get stock wanted weeks from main form
    let stock_wanted_weeks = flt(frm.doc.stock_wantedweeks) || 0;
    console.log('Stock wanted weeks:', stock_wanted_weeks);
    
    if (stock_wanted_weeks <= 0) {
        console.log('Stock wanted weeks is 0 or negative');
        frappe.msgprint({
            title: __('Missing Data'),
            indicator: 'orange',
            message: __('Please set Stock Wanted(Weeks) value first (must be > 0).')
        });
        return;
    }

    valid_consumption.sort((a, b) => {
        // Get item name for sorting with better error handling
        let item_name_a = a.item || '';
        let item_name_b = b.item || '';
        
        try {
            if (frappe.db.exists("Item", a.item)) {
                let item_doc_a = frappe.get_doc("Item", a.item);
                if (item_doc_a && item_doc_a.item_name) {
                    item_name_a = item_doc_a.item_name;
                }
            }
        } catch (e) {
            console.log('Could not get item name for:', a.item, 'using item code instead');
        }
        
        try {
            if (frappe.db.exists("Item", b.item)) {
                let item_doc_b = frappe.get_doc("Item", b.item);
                if (item_doc_b && item_doc_b.item_name) {
                    item_name_b = item_doc_b.item_name;
                }
            }
        } catch (e) {
            console.log('Could not get item name for:', b.item, 'using item code instead');
        }
        
        return item_name_a.localeCompare(item_name_b);
    }).forEach(consumption => {
        console.log('Processing consumption row:', consumption);
        
        // Get item name for display with better error handling
        let item_name = consumption.item || '';
        try {
            if (frappe.db.exists("Item", consumption.item)) {
                let item_doc = frappe.get_doc("Item", consumption.item);
                if (item_doc && item_doc.item_name) {
                    item_name = item_doc.item_name;
                }
            }
        } catch (e) {
            console.log('Could not get item name for display for:', consumption.item, 'using item code instead');
        }
        
        let current_stock = stock_map[consumption.item] || {
            tima_1: 0, tima_2: 0, tima_3: 0, tima_4: 0,
            tima_5: 0, tima_6: 0, tima_7: 0, jangwani: 0
        };
        
        // Calculate required stock and order quantity for each farm
        // Use the farm-specific consumption data from the child table
        let required_stock_tima_1 = flt(consumption.tima_1) * stock_wanted_weeks;
        let required_stock_tima_2 = flt(consumption.tima_2) * stock_wanted_weeks;
        let required_stock_tima_3 = flt(consumption.tima_3) * stock_wanted_weeks;
        let required_stock_tima_4 = flt(consumption.tima_4) * stock_wanted_weeks;
        let required_stock_tima_5 = flt(consumption.tima_5) * stock_wanted_weeks;
        let required_stock_tima_6 = flt(consumption.tima_6) * stock_wanted_weeks;
        let required_stock_tima_7 = flt(consumption.tima_7) * stock_wanted_weeks;
        let required_stock_jangwani = flt(consumption.jangwani) * stock_wanted_weeks;
        
        console.log('Calculated required stock for', consumption.item, ':', {
            tima_1: required_stock_tima_1,
            tima_2: required_stock_tima_2,
            tima_3: required_stock_tima_3,
            tima_4: required_stock_tima_4,
            tima_5: required_stock_tima_5,
            tima_6: required_stock_tima_6,
            tima_7: required_stock_tima_7,
            jangwani: required_stock_jangwani
        });
        
        // Add to order quantity table
        let order_row = frm.add_child('order_quantity', {
            item: consumption.item,
            item_name: item_name,
            tima_1: Math.ceil(Math.max(0, required_stock_tima_1 - current_stock.tima_1)),
            tima_2: Math.ceil(Math.max(0, required_stock_tima_2 - current_stock.tima_2)),
            tima_3: Math.ceil(Math.max(0, required_stock_tima_3 - current_stock.tima_3)),
            tima_4: Math.ceil(Math.max(0, required_stock_tima_4 - current_stock.tima_4)),
            tima_5: Math.ceil(Math.max(0, required_stock_tima_5 - current_stock.tima_5)),
            tima_6: Math.ceil(Math.max(0, required_stock_tima_6 - current_stock.tima_6)),
            tima_7: Math.ceil(Math.max(0, required_stock_tima_7 - current_stock.tima_7)),
            jangwani: Math.ceil(Math.max(0, required_stock_jangwani - current_stock.jangwani))
        });
        
        calculated_count++;
        console.log('Added order row for', consumption.item);
    });

    console.log('Total calculated:', calculated_count);

    frm.refresh_field('order_quantity');
    
    if (calculated_count > 0) {
        frm.save().then(() => {
            console.log('Order quantities saved successfully');
            frappe.show_alert({
                message: __('Calculated order quantities for {0} items').replace('{0}', calculated_count) + 
                        (skipped_count > 0 ? __(', skipped {0} items').replace('{0}', skipped_count) : ''),
                indicator: 'green'
            }, 5);
        });
    } else {
        console.log('No items calculated');
        frappe.msgprint(__('No items met the criteria for order calculation.'));
    }
    
    console.log('=== CALCULATE ORDER QUANTITIES COMPLETED ===');
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
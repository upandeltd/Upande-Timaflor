frappe.ui.form.on('Fertilizer Order Sheet', {
    refresh: function(frm) {
        // Add custom buttons
        frm.add_custom_button(__('Refresh Stock Levels'), function() {
            refresh_stock_levels(frm);
        }).addClass('btn-primary');

        frm.add_custom_button(__('Add All Fertilizers'), function() {
            add_all_fertilizers(frm);
        }).addClass('btn-success');

        frm.add_custom_button(__('Calculate Order Quantities'), function() {
            calculate_order_quantities(frm);
        }).addClass('btn-info');

        frm.add_custom_button(__('Clean Up Data'), function() {
            cleanup_consumption_data(frm);
        }).addClass('btn-warning');

        // Debug buttons
        frm.add_custom_button(__('Debug Data'), function() {
            debug_fertilizer_data(frm);
        }, __('Debug'));

        frm.add_custom_button(__('Validate Setup'), function() {
            validate_setup(frm);
        }, __('Debug'));

        frm.add_custom_button(__('Debug Consumption'), function() {
            debug_consumption_table(frm);
        }, __('Debug'));
    },

    average_consumption: function(frm) {
        update_consumption_for_all_rows(frm);
    },

    stock_wanted_weeks: function(frm) {
        update_stock_wanted_for_all_rows(frm);
    }
});

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

function cleanup_consumption_data(frm) {
    if (!frm.doc.name) {
        frappe.msgprint('Please save the document first');
        return;
    }
    
    frappe.confirm(
        'This will remove all invalid rows from the consumption table. Continue?',
        function() {
            frappe.call({
                method: 'upande_timaflor.upande_timaflor.doctype.fertilizer_order_sheet.fertilizer_order_sheet.cleanup_consumption_table',
                args: { docname: frm.doc.name },
                freeze: true,
                freeze_message: __('Cleaning up data...'),
                callback: function(r) {
                    if (r.message && !r.message.error) {
                        frappe.show_alert(r.message.message, 'green');
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: r.message?.error || 'Cleanup failed'
                        });
                    }
                }
            });
        }
    );
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
    let invalid_rows = consumption_data.filter(row => 
        !row.item || !row.item_name || 
        row.item.trim() === '' || row.item_name.trim() === ''
    );
    
    if (invalid_rows.length > 0) {
        frappe.msgprint({
            title: __('Data Validation Error'),
            indicator: 'red',
            message: __('Found {0} rows with missing item names or codes. Please use "Clean Up Data" button to fix this.').replace('{0}', invalid_rows.length)
        });
        return;
    }

    // Proceed with calculation
    calculate_order_quantities_after_validation(frm);
}

function calculate_order_quantities_after_validation(frm) {
    let consumption_data = frm.doc.weekly_average_consumption || [];
    let stock_data = frm.doc.stock_levels || [];
    let main_avg_consumption = parseFloat(frm.doc.average_consumption) || 0;
    let main_stock_wanted_weeks = parseFloat(frm.doc.stock_wanted_weeks) || 0;

    // Create stock lookup map
    let stock_map = {};
    stock_data.forEach(stock => {
        stock_map[stock.item_code] = parseFloat(stock.total_stock) || 0;
        stock_map[stock.item_name] = parseFloat(stock.total_stock) || 0;
        stock_map[stock.item] = parseFloat(stock.total_stock) || 0;
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
        let row_avg_consumption = parseFloat(consumption.average_consumption) || 0;
        let row_stock_wanted_weeks = parseFloat(consumption.stock_wanted_weeks) || 0;
        
        // Use row values if available, otherwise use main form values
        let avg_consumption = row_avg_consumption > 0 ? row_avg_consumption : main_avg_consumption;
        let stock_wanted_weeks = row_stock_wanted_weeks > 0 ? row_stock_wanted_weeks : main_stock_wanted_weeks;

        if (avg_consumption > 0 && stock_wanted_weeks > 0) {
            // Look up current stock using multiple keys
            let current_stock = stock_map[consumption.item] || 
                              stock_map[consumption.item_name] || 
                              0;
            
            let required_stock = avg_consumption * stock_wanted_weeks;
            let order_qty = Math.ceil(Math.max(0, required_stock - current_stock));
            
            // Add to order quantity table
            frm.add_child('order_quantity', {
                item: consumption.item,  // Item code
                item_name: consumption.item_name,  // Item name
                current_stock: current_stock,
                average_consumption_per_week: avg_consumption,
                weeks_to_order_for: stock_wanted_weeks,
                required_stock: required_stock,
                calculated_order_quantity: order_qty
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
frappe.ui.form.on('Ordering Sheet', {
    before_save: function(frm) {
        console.log("Trigger: before_save Fired");

        if (!frm.doc.daily_average_consumptiondays || !frm.doc.table_bvnr) {
            console.log("Missing Required Data");
            return;
        }

        let requests = frm.doc.table_bvnr.map(row => {
            return new Promise(resolve => {
                frappe.call({
                    method: 'upande_timaflor.upande_timaflor.doctype.ordering_sheet.ordering_sheet.get_average_consumption',
                    args: {
                        item_code: row.item,
                        from_date: frappe.datetime.add_days(frappe.datetime.nowdate(), -frm.doc.daily_average_consumptiondays),
                        to_date: frappe.datetime.nowdate()
                    },
                    callback: function(r) {
                        if (!r.exc && r.message !== undefined) {
                            console.log(`API Response for ${row.item}:`, r.message);
                            const farmMap = {
                                "Tima1": "t1_avg",
                                "Tima2": "t2_avg",
                                "Tima3": "t3_avg",
                                "Tima4": "t4_avg",
                                "Tima5": "t5_avg",
                                "Tima6": "t6_avg",
                                "Tima7": "t7_avg",
                                //"Jangwani": "jangwani_avg"
                            };

                            // Initialize averages to 0
                            Object.values(farmMap).forEach(field => {
                                frappe.model.set_value(row.doctype, row.name, field, 0);
                            });

                            // Update averages in table_bvnr
                            Object.entries(r.message).forEach(([farm, avg]) => {
                                const field = farmMap[farm];
                                if (field) {
                                    frappe.model.set_value(row.doctype, row.name, field, avg);
                                }
                            });
                        }
                        resolve();
                    }
                });
            });
        });

        Promise.all(requests).then(() => {
            console.log("API Calls Finished, Now Calculating Quantities");
            calculate_order_quantities(frm);
            frm.refresh_field("table_bvnr");
            frm.refresh_field("order_quantity"); 
        });
    }
});

function calculate_order_quantities(frm) {
    console.log("Trigger: Order Quantity Calculation");

    if (!frm.doc.ordering_quantity || !frm.doc.table_bvnr) return;

    // Clear existing order quantity entries
    frm.doc.order_quantity = [];

    frm.doc.table_bvnr.forEach(avg_row => {
        let order_qty = frm.doc.ordering_quantity;
        let order_row = frappe.model.add_child(frm.doc, "Order Quantity", "order_quantity");
        
        // Copy item from averages table
        order_row.item = avg_row.item;

        // Calculate and set order quantities
        order_row.tima_1 = (avg_row.t1_avg || 0) * order_qty;
        order_row.tima_2 = (avg_row.t2_avg || 0) * order_qty;
        order_row.tima_3 = (avg_row.t3_avg || 0) * order_qty;
        order_row.tima_4 = (avg_row.t4_avg || 0) * order_qty;
        order_row.tima_5 = (avg_row.t5_avg || 0) * order_qty;
        order_row.tima_6 = (avg_row.t6_avg || 0) * order_qty;
        order_row.tima_7 = (avg_row.t7_avg || 0) * order_qty;
        //order_row.Jangwani = (avg_row.jangwani_avg || 0) * order_qty;
    });

    frm.refresh_field("order_quantity");
}
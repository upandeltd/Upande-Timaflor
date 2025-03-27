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
                            frappe.model.set_value(row.doctype, row.name, 't1_avg', r.message);
                        } else {
                            console.log(`API Failed for ${row.item}`);
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
        });
    }
});

function calculate_order_quantities(frm) {
    console.log("Trigger: Order Quantity Calculation");

    if (!frm.doc.ordering_quantity || !frm.doc.table_bvnr) return;

    frm.doc.table_bvnr.forEach(row => {
        let order_qty = frm.doc.ordering_quantity;

        // Calculate values
        let tima_1 = row.t1_avg * order_qty || 0;
        let tima_2 = row.t2_avg * order_qty || 0;
        let tima_3 = row.t3_avg * order_qty || 0;
        let tima_4 = row.t4_avg * order_qty || 0;
        let tima_5 = row.t5_avg * order_qty || 0;
        let tima_6 = row.t6_avg * order_qty || 0;
        let tima_7 = row.t7_avg * order_qty || 0;
        let jangwani = row.jangwani_avg * order_qty || 0;

        // Update fields
        frappe.model.set_value(row.doctype, row.name, 'tima_1', tima_1);
        frappe.model.set_value(row.doctype, row.name, 'tima_2', tima_2);
        frappe.model.set_value(row.doctype, row.name, 'tima_3', tima_3);
        frappe.model.set_value(row.doctype, row.name, 'tima_4', tima_4);
        frappe.model.set_value(row.doctype, row.name, 'tima_5', tima_5);
        frappe.model.set_value(row.doctype, row.name, 'tima_6', tima_6);
        frappe.model.set_value(row.doctype, row.name, 'tima_7', tima_7);
        frappe.model.set_value(row.doctype, row.name, 'jangwani', jangwani);

        // Log calculated values
        console.log(`Item: ${row.item} | Order Qty: ${order_qty}`);
        console.log({
            "T1": tima_1,
            "T2": tima_2,
            "T3": tima_3,
            "T4": tima_4,
            "T5": tima_5,
            "T6": tima_6,
            "T7": tima_7,
            "Jangwani": jangwani
        });

        console.log(`Updated ${row.item}: Order Qty Calculated`);
    });

    frm.refresh_field("table_bvnr");
}

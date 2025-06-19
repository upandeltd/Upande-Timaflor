// Material Request - Get Items From
// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts.dimensions");
frappe.provide("erpnext.buying");

erpnext.buying.setup_buying_controller();

frappe.ui.form.on("Material Request", {
    setup: function (frm) {
        frm.custom_make_buttons = {
            "Stock Entry": "Issue Material",
            "Pick List": "Pick List",
            "Purchase Order": "Purchase Order",
            "Request for Quotation": "Request for Quotation",
            "Supplier Quotation": "Supplier Quotation",
            "Work Order": "Work Order",
            "Purchase Receipt": "Purchase Receipt",
        };

        // formatter for material request item
        frm.set_indicator_formatter("item_code", function (doc) {
            return doc.stock_qty <= doc.ordered_qty ? "green" : "orange";
        });

        frm.set_query("item_code", "items", function () {
            return {
                query: "erpnext.controllers.queries.item_query",
            };
        });

        frm.set_query("from_warehouse", "items", function (doc) {
            return {
                filters: { company: doc.company },
            };
        });

        frm.set_query("bom_no", "items", function (doc, cdt, cdn) {
            var row = locals[cdt][cdn];
            return {
                filters: {
                    item: row.item_code,
                },
            };
        });
    },

    onload: function (frm) {
        // add item, if previous view was item
        erpnext.utils.add_item(frm);

        // set schedule_date
        set_schedule_date(frm);

        frm.set_query("warehouse", "items", function (doc) {
            return {
                filters: { company: doc.company },
            };
        });

        frm.set_query("set_warehouse", function (doc) {
            return {
                filters: { company: doc.company },
            };
        });

        frm.set_query("set_from_warehouse", function (doc) {
            return {
                filters: { company: doc.company },
            };
        });

        erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
    },

    company: function (frm) {
        erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
    },

    onload_post_render: function (frm) {
        frm.get_field("items").grid.set_multiple_add("item_code", "qty");
    },

    refresh: function (frm) {
        frm.events.make_custom_buttons(frm);
        frm.toggle_reqd("customer", frm.doc.material_request_type == "Customer Provided");

        // Add "Create Filtered PO" button for submitted Purchase Material Requests
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.material_request_type === "Purchase" &&
            frm.doc.status != "Stopped"
        ) {
            frm.add_custom_button(__("Create Filtered PO"), () => frm.events.create_filtered_purchase_order(frm), __("Create"));
        }

        // Make 'custom_approver' field read-only if flagged by backend
        if (frm.doc.approver_read_only) {
            frm.set_df_property('custom_approver', 'read_only', 1);
        }

        // Notify the approver after submission
        if (frm.doc.docstatus === 1 && frm.doc.custom_approver) {
            frappe.show_alert({
                message: __("Notification sent to approver: {0}", [frm.doc.custom_approver]),
                indicator: "green"
            });
        }
    },

    set_from_warehouse: function (frm) {
        if (frm.doc.material_request_type == "Material Transfer" && frm.doc.set_from_warehouse) {
            frm.doc.items.forEach((d) => {
                frappe.model.set_value(d.doctype, d.name, "from_warehouse", frm.doc.set_from_warehouse);
            });
        }
    },

    make_custom_buttons: function (frm) {
        if (frm.doc.docstatus == 0) {
            frm.add_custom_button(
                __("Bill of Materials"),
                () => frm.events.get_items_from_bom(frm),
                __("Get Items From")
            );
        }

        // Add the new Material Request button here
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Material Request (Transfer)"),
                () => frm.events.get_items_from_material_request_transfer(frm),
                __("Get Items From")
            );
        }

        if (frm.doc.docstatus == 1 && frm.doc.status != "Stopped") {
            let precision = frappe.defaults.get_default("float_precision");

            if (flt(frm.doc.per_received, precision) < 100) {
                frm.add_custom_button(__("Stop"), () => frm.events.update_status(frm, "Stopped"));

                if (frm.doc.material_request_type === "Purchase") {
                    frm.add_custom_button(
                        __("Purchase Order"),
                        () => frm.events.make_purchase_order(frm),
                        __("Create")
                    );
                }
            }

            if (flt(frm.doc.per_ordered, precision) < 100) {
                let add_create_pick_list_button = () => {
                    frm.add_custom_button(
                        __("Pick List"),
                        () => frm.events.create_pick_list(frm),
                        __("Create")
                    );
                };

                if (frm.doc.material_request_type === "Material Transfer") {
                    add_create_pick_list_button();
                    frm.add_custom_button(
                        __("Material Transfer"),
                        () => frm.events.make_stock_entry(frm),
                        __("Create")
                    );

                    frm.add_custom_button(
                        __("Material Transfer (In Transit)"),
                        () => frm.events.make_in_transit_stock_entry(frm),
                        __("Create")
                    );
                }

                if (frm.doc.material_request_type === "Material Issue") {
                    frm.add_custom_button(
                        __("Issue Material"),
                        () => frm.events.make_stock_entry(frm),
                        __("Create")
                    );
                }

                if (frm.doc.material_request_type === "Customer Provided") {
                    frm.add_custom_button(
                        __("Material Receipt"),
                        () => frm.events.make_stock_entry(frm),
                        __("Create")
                    );
                }

                if (frm.doc.material_request_type === "Purchase") {
                    frm.add_custom_button(
                        __("Request for Quotation"),
                        () => frm.events.make_request_for_quotation(frm),
                        __("Create")
                    );
                }

                if (frm.doc.material_request_type === "Purchase") {
                    frm.add_custom_button(
                        __("Supplier Quotation"),
                        () => frm.events.make_supplier_quotation(frm),
                        __("Create")
                    );
                }

                if (frm.doc.material_request_type === "Manufacture") {
                    frm.add_custom_button(
                        __("Work Order"),
                        () => frm.events.raise_work_orders(frm),
                        __("Create")
                    );
                }

                frm.page.set_inner_btn_group_as_primary(__("Create"));
            }
        }

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Sales Order"),
                () => frm.events.get_items_from_sales_order(frm),
                __("Get Items From")
            );
        }

        if (frm.doc.docstatus == 1 && frm.doc.status == "Stopped") {
            frm.add_custom_button(__("Re-open"), () => frm.events.update_status(frm, "Submitted"));
        }
    },

    update_status: function (frm, stop_status) {
        frappe.call({
            method: "erpnext.stock.doctype.material_request.material_request.update_status",
            args: { name: frm.doc.name, status: stop_status },
            callback(r) {
                if (!r.exc) {
                    frm.reload_doc();
                }
            },
        });
    },

    create_filtered_purchase_order: function (frm) {
        // ... (existing function content unchanged) ...
    },

    get_item_data: function (frm, item, overwrite_warehouse = false) {
        // ... (existing function content unchanged) ...
    },

    get_items_from_bom: function (frm) {
        // ... (existing function content unchanged) ...
    },

    make_purchase_order: function (frm) {
        // ... (existing function content unchanged) ...
    },

    make_request_for_quotation: function (frm) {
        // ... (existing function content unchanged) ...
    },

    make_supplier_quotation: function (frm) {
        // ... (existing function content unchanged) ...
    },

    make_stock_entry: function (frm) {
        // ... (existing function content unchanged) ...
    },

    make_in_transit_stock_entry(frm) {
        // ... (existing function content unchanged) ...
    },

    create_pick_list: (frm) => {
        // ... (existing function content unchanged) ...
    },

    raise_work_orders: function (frm) {
        // ... (existing function content unchanged) ...
    },

    material_request_type: function (frm) {
        frm.toggle_reqd("customer", frm.doc.material_request_type == "Customer Provided");

        if (frm.doc.material_request_type !== "Material Transfer" && frm.doc.set_from_warehouse) {
            frm.set_value("set_from_warehouse", "");
        }
    },
});

frappe.ui.form.on("Material Request Item", {
    qty: function (frm, doctype, name) {
        const item = locals[doctype][name];
        if (flt(item.qty) < flt(item.min_order_qty)) {
            frappe.msgprint(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
        }
        frm.events.get_item_data(frm, item, false);
    },

    from_warehouse: function (frm, doctype, name) {
        const item = locals[doctype][name];
        frm.events.get_item_data(frm, item, false);
    },

    warehouse: function (frm, doctype, name) {
        const item = locals[doctype][name];
        frm.events.get_item_data(frm, item, false);
    },

    rate(frm, doctype, name) {
        const item = locals[doctype][name];
        item.amount = flt(item.qty) * flt(item.rate);
        frappe.model.set_value(doctype, name, "amount", item.amount);
        refresh_field("amount", item.name, item.parentfield);
    },

    item_code: function (frm, doctype, name) {
        const item = locals[doctype][name];
        item.rate = 0;
        item.uom = "";
        set_schedule_date(frm);
        frm.events.get_item_data(frm, item, true);
    },

    schedule_date: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.schedule_date) {
            if (!frm.doc.schedule_date) {
                erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
            } else {
                set_schedule_date(frm);
            }
        }
    },

    conversion_factor: function (frm, doctype, name) {
        const item = locals[doctype][name];
        frm.events.get_item_data(frm, item, false);
    },
});

erpnext.buying.MaterialRequestController = class MaterialRequestController extends (
    erpnext.buying.BuyingController
) {
    // Methods unchanged from your original content...
};

// for backward compatibility: combine new and previous states
extend_cscript(cur_frm.cscript, new erpnext.buying.MaterialRequestController({ frm: cur_frm }));

function set_schedule_date(frm) {
    if (frm.doc.schedule_date) {
        erpnext.utils.copy_value_in_all_rows(
            frm.doc,
            frm.doc.doctype,
            frm.doc.name,
            "items",
            "schedule_date"
        );
    }
}
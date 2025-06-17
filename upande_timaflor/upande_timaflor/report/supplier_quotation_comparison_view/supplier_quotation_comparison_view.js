frappe.query_reports["Supplier Quotation Comparison View"] = {
    filters: [
        {
            fieldname: "rfq",
            label: __("Request for Quotation"), // Localize label
            fieldtype: "Link",
            options: "Request for Quotation",
            reqd: 1
        }
    ],

    onload: function (report) {
        report.page.add_inner_button(__("Create Purchase Orders"), function () { // Localize button label
            const selected = getSelectedQuotations();

            if (selected.length === 0) {
                return frappe.msgprint(__("Please select at least one quotation item.")); // Localize message
            }

            frappe.confirm(__("Create Purchase Orders for selected items?"), () => { // Localize message
                frappe.show_progress(__("Creating Purchase Orders..."), 100, 100, __("Please wait")); // Localize messages

                frappe.call({
                    // IMPORTANT: Replace 'your_app_name.your_module_name.report.rfq_comparison_report.rfq_comparison_report'
                    // with the actual full path to your Python script's create_purchase_orders_from_rfq function.
                    // Example: 'my_custom_app.my_module.report.supplier_quotation_comparison_view.supplier_quotation_comparison_view.create_purchase_orders_from_rfq'
                    method: "upande_timaflor.upande_timaflor.report.supplier_quotation_comparison_view.supplier_quotation_comparison_view.create_purchase_orders_from_rfq",
                    args: { selections: JSON.stringify(selected) },
                    callback: function (r) {
                        frappe.hide_progress();
                        if (r.message && r.message.purchase_orders && r.message.purchase_orders.length > 0) {
                            const links = r.message.purchase_orders.map(name =>
                                `<li><a href="/app/purchase-order/${name}" target="_blank">${name}</a></li>`
                            ).join("");

                            frappe.msgprint({
                                title: __("Purchase Orders Created"), // Localize title
                                message: `<ul>${links}</ul>`,
                                indicator: "green"
                            });

                            frappe.set_route("List", "Purchase Order");
                        } else if (r.exc) { // If there's an exception from the server
                             frappe.msgprint({
                                title: __("Error"),
                                message: __("An error occurred while creating Purchase Orders. Please check the console for details."),
                                indicator: "red"
                            });
                            console.error(r.exc); // Log the full exception for debugging
                        } else {
                            // Catch cases where no POs are created, but no explicit error is thrown by backend
                            frappe.msgprint(__("No Purchase Orders were created.")); // Localize message
                        }
                    },
                    error: function (err) {
                        frappe.hide_progress();
                        frappe.msgprint(__("Unable to create Purchase Orders. An unexpected error occurred.")); // Localize message
                        console.error(err);
                    }
                });
            });
        });
    }
};

// Collects checked checkbox data from the table
function getSelectedQuotations() {
    return Array.from(document.querySelectorAll(".sq-select:checked")).map(checkbox => {
        // Retrieve all data attributes directly from the checkbox
        const data = checkbox.dataset;

        return {
            item_code: data.item,
            item_name: data.itemName,
            uom: data.uom,
            qty: parseFloat(data.qty), // Ensure qty is parsed as a float
            rate: parseFloat(data.rate),
            supplier: data.supplier,
            currency: data.currency // Add currency from data attribute
        };
    });
}

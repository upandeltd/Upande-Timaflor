/* global frappe */
frappe.query_reports["Account Ledger View"] = {
    filters: [
        {
            fieldname: "account",
            label: __("Account"),
            fieldtype: "Link",
            options: "Account",
            reqd: 0,
            on_change: () => {
                const acc = frappe.query_report.get_filter_value("account");
                if (acc) {
                    frappe.db.get_value("Account", acc, "account_name").then(r => {
                        const name = r.message.account_name;
                        frappe.query_report.page.set_title(__("Ledger for {0}", [name]));
                    });
                } else {
                    frappe.query_report.page.set_title(__("Account Ledger Summary"));
                }

                // Force report refresh when account is changed
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        }
    ],

    onload: function (report) {
        // Add "Back to Summary" button
        const backBtn = report.page.add_inner_button(__("Back to Summary"), () => {
            frappe.query_report.set_filter_value("account", "");
            frappe.query_report.refresh();
        });

        const acc = frappe.query_report.get_filter_value("account");

        if (acc) {
            frappe.db.get_value("Account", acc, "account_name").then(r => {
                const name = r.message.account_name;
                report.page.set_title(__("Ledger for {0}", [name]));
            });
            backBtn.$button.show();
        } else {
            report.page.set_title(__("Account Ledger Summary"));
            backBtn.$button.hide(); // Hide button in summary mode
        }

        // Inject custom styles
        const style = `
            a[data-ledger-account] {
                color: var(--text-on-light);
                text-decoration: none;
                font-weight: 500;
            }
            a[data-ledger-account]:hover {
                text-decoration: underline;
                color: var(--primary);
            }
            .text-green { color: #2e7d32 !important; }
            .text-red { color: #c62828 !important; }
            .text-gray { color: #9e9e9e !important; }
        `;
        const styleTag = document.createElement("style");
        styleTag.innerHTML = style;
        document.head.appendChild(styleTag);
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        const is_summary_mode = !frappe.query_report.get_filter_value("account");
        if (
            is_summary_mode &&
            ["account_name", "account", "account_number"].includes(column.fieldname) &&
            data && data.account
        ) {
            value = `<a href="#" data-ledger-account="${data.account}">${value}</a>`;
        }

        if (["balance", "balance_in_account_currency"].includes(column.fieldname)) {
            const amount = parseFloat(data[column.fieldname]) || 0;
            if (amount > 0) {
                value = `<span class="text-green">${value}</span>`;
            } else if (amount < 0) {
                value = `<span class="text-red">${value}</span>`;
            } else {
                value = `<span class="text-gray">${value}</span>`;
            }
        }

        return value;
    },

    after_datatable_render: function (report) {
        // Clickable account links in summary view
        report.$wrapper.on('click', 'a[data-ledger-account]', function (e) {
            e.preventDefault();
            const acc = $(this).data('ledger-account');
            frappe.query_report.set_filter_value('account', acc);
            frappe.query_report.refresh();
        });
    }
};

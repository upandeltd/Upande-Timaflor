// ~/frappe-bench/apps/upande_timaflor/upande_timaflor/report/custom_general_ledger/custom_general_ledger.js

frappe.query_reports["Custom General Ledger"] = {
  onload: function(report) {
    frappe.call({
      method: "upande_timaflor.report.custom_general_ledger.custom_general_ledger.get_account_title",
      args: { account: report.get_filter_value("account") },
      callback: function(r) {
        if (r.message) {
          $(".title-text").text("Ledger for: " + r.message);
        }
      }
    });
  },
  filters: [
    {
      fieldname: "account",
      label: "Account",
      fieldtype: "Link",
      options: "Account",
      reqd: 1
    }
  ]
}

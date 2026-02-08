// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Balance Sheet"] = $.extend({}, erpnext.financial_statements);

// Disable tree mode — show flat table with level columns instead
delete frappe.query_reports["Balance Sheet"]["tree"];
delete frappe.query_reports["Balance Sheet"]["name_field"];
delete frappe.query_reports["Balance Sheet"]["parent_field"];
delete frappe.query_reports["Balance Sheet"]["initial_depth"];

erpnext.utils.add_dimensions("Balance Sheet", 10);

frappe.query_reports["Balance Sheet"]["filters"].push(
	{
		fieldname: "selected_view",
		label: __("Select View"),
		fieldtype: "Select",
		options: [
			{ value: "Report", label: __("Report View") },
			{ value: "Growth", label: __("Growth View") },
		],
		default: "Report",
		reqd: 1,
	},
	{
		fieldname: "accumulated_values",
		label: __("Accumulated Values"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "include_default_book_entries",
		label: __("Include Default FB Entries"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "show_zero_values",
		label: __("Show zero values"),
		fieldtype: "Check",
	},
	{
		fieldname: "hide_group_accounts",
		label: __("Hide Group Accounts"),
		fieldtype: "Check",
	}
);

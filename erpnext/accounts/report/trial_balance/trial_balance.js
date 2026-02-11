// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Trial Balance"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(date=frappe.datetime.get_today(), company=frappe.query_report.get_filter_value("company")),
			reqd: 1,
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
					},
				};
			},
			on_change: function (query_report) {
				var fiscal_year = query_report.get_values().fiscal_year;
				if (!fiscal_year) {
					return;
				}
				frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
					var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
					frappe.query_report.set_filter_value({
						from_date: fy.year_start_date,
						to_date: fy.year_end_date,
					});
				});
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					doctype: "Cost Center",
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "with_period_closing_entry_for_opening",
			label: __("With Period Closing Entry For Opening Balances"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "with_period_closing_entry_for_current_period",
			label: __("Period Closing Entry For Current Period"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_zero_values",
			label: __("Show zero values"),
			fieldtype: "Check",
		},
		{
			fieldname: "show_unclosed_fy_pl_balances",
			label: __("Show unclosed fiscal year's P&L balances"),
			fieldtype: "Check",
		},
		{
			fieldname: "include_default_book_entries",
			label: __("Include Default FB Entries"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "show_net_values",
			label: __("Show net values in opening and closing columns"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "hide_group_accounts",
			label: __("Hide Group Accounts"),
			fieldtype: "Check",
		},
		{
			fieldname: "fill_columns",
			label: __("Fill Columns"),
			fieldtype: "Check",
		},
	],
	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 3,
	formatter: erpnext.financial_statements.formatter,
};

erpnext.utils.add_dimensions("Trial Balance", 6);

// CSS to remove DataTable's inline indentation (hierarchy shown via level columns)
let _tb_style_id = "tb-tree-no-indent-style";
function _tb_inject_css() {
	if (!document.getElementById(_tb_style_id)) {
		let style = document.createElement("style");
		style.id = _tb_style_id;
		style.textContent = `
			.dt-tree-node[style] { padding-left: 0 !important; display: block !important; }
			.dt-tree-node__toggle[style] { left: 0 !important; }
		`;
		document.head.appendChild(style);
	}
}
function _tb_remove_css() {
	let el = document.getElementById(_tb_style_id);
	if (el) el.remove();
}

let _tb_original_onload = frappe.query_reports["Trial Balance"]["onload"];
frappe.query_reports["Trial Balance"]["onload"] = function (report) {
	if (_tb_original_onload) _tb_original_onload.call(this, report);
	_tb_inject_css();
	$(document).off("page-change.tb_css").on("page-change.tb_css", function () {
		if (frappe.get_route_str() !== "query-report/Trial Balance") {
			_tb_remove_css();
			$(document).off("page-change.tb_css");
		}
	});
};

// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Profit and Loss Statement"] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions("Profit and Loss Statement", 10);

frappe.query_reports["Profit and Loss Statement"]["filters"].push(
	{
		fieldname: "selected_view",
		label: __("Select View"),
		fieldtype: "Select",
		options: [
			{ value: "Report", label: __("Report View") },
			{ value: "Growth", label: __("Growth View") },
			{ value: "Margin", label: __("Margin View") },
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
	},
	{
		fieldname: "fill_columns",
		label: __("Fill Columns"),
		fieldtype: "Check",
	},
	{
		fieldname: "show_chart",
		label: __("Show Chart"),
		fieldtype: "Check",
	}
);

// CSS to remove DataTable's inline indentation (hierarchy shown via level columns)
let _pl_style_id = "pl-tree-no-indent-style";
function _pl_inject_css() {
	if (!document.getElementById(_pl_style_id)) {
		let style = document.createElement("style");
		style.id = _pl_style_id;
		style.textContent = `
			.dt-tree-node[style] { padding-left: 0 !important; display: block !important; }
			.dt-tree-node__toggle[style] { left: 0 !important; }
		`;
		document.head.appendChild(style);
	}
}
function _pl_remove_css() {
	let el = document.getElementById(_pl_style_id);
	if (el) el.remove();
}

let _pl_original_onload = frappe.query_reports["Profit and Loss Statement"]["onload"];
frappe.query_reports["Profit and Loss Statement"]["onload"] = function (report) {
	if (_pl_original_onload) _pl_original_onload.call(this, report);
	_pl_inject_css();
	$(document).off("page-change.pl_css").on("page-change.pl_css", function () {
		if (frappe.get_route_str() !== "query-report/Profit and Loss Statement") {
			_pl_remove_css();
			$(document).off("page-change.pl_css");
		}
	});
};

// Override formatter to handle level columns (skip growth/margin formatting, add GL link)
let _pl_original_formatter = frappe.query_reports["Profit and Loss Statement"]["formatter"];
frappe.query_reports["Profit and Loss Statement"]["formatter"] = function (value, row, column, data, default_formatter, filter) {
	if (column.fieldname && (column.fieldname.startsWith("level_") || column.fieldname === "is_group")) {
		if (data && column.fieldname.startsWith("level_") && value && data.account) {
			column.link_onclick =
				"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
		}
		value = default_formatter(value, row, column, data);
		if (data && !data.parent_account && !data.parent_section) {
			value = $(`<span>${value}</span>`).css("font-weight", "bold").wrap("<p></p>").parent().html();
		}
		return value;
	}
	return _pl_original_formatter.call(this, value, row, column, data, default_formatter, filter);
};

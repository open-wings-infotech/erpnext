// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Balance Sheet"] = $.extend({}, erpnext.financial_statements);

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

// CSS to remove DataTable's inline indentation (hierarchy shown via level columns instead)
// Scoped: injected on report load, removed on navigation to avoid affecting other tree reports
let _bs_style_id = "bs-tree-no-indent-style";
function _bs_inject_css() {
	if (!document.getElementById(_bs_style_id)) {
		let style = document.createElement("style");
		style.id = _bs_style_id;
		style.textContent = `
			.dt-tree-node[style] { padding-left: 0 !important; display: block !important; }
			.dt-tree-node__toggle[style] { left: 0 !important; }
		`;
		document.head.appendChild(style);
	}
}
function _bs_remove_css() {
	let el = document.getElementById(_bs_style_id);
	if (el) el.remove();
}

// Inject CSS on report load, remove on navigation away
let _bs_original_onload = frappe.query_reports["Balance Sheet"]["onload"];
frappe.query_reports["Balance Sheet"]["onload"] = function (report) {
	if (_bs_original_onload) _bs_original_onload.call(this, report);
	_bs_inject_css();
	// Remove CSS when user navigates away from this report
	$(document).off("page-change.bs_css").on("page-change.bs_css", function () {
		if (frappe.get_route_str() !== "query-report/Balance Sheet") {
			_bs_remove_css();
			$(document).off("page-change.bs_css");
		}
	});
};

// Override formatter to handle level columns (skip growth formatting, add GL link)
let _bs_original_formatter = frappe.query_reports["Balance Sheet"]["formatter"];
frappe.query_reports["Balance Sheet"]["formatter"] = function (value, row, column, data, default_formatter, filter) {
	// For level columns and is_group, handle separately to avoid growth view interference
	if (column.fieldname && (column.fieldname.startsWith("level_") || column.fieldname === "is_group")) {
		// Add General Ledger onclick for level columns with values
		if (data && column.fieldname.startsWith("level_") && value && data.account) {
			column.link_onclick =
				"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
		}
		// Use default formatter (no growth/margin special handling)
		value = default_formatter(value, row, column, data);
		// Bold for total rows (root-level accounts)
		if (data && !data.parent_account && !data.parent_section) {
			value = $(`<span>${value}</span>`).css("font-weight", "bold").wrap("<p></p>").parent().html();
		}
		return value;
	}

	// For all other columns, use the original formatter
	return _bs_original_formatter.call(this, value, row, column, data, default_formatter, filter);
};

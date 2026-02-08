# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	compute_growth_view_data,
	compute_margin_view_data,
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)


def execute(filters=None):
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

	# Post-process: add ancestor level columns and is_group
	data, columns = add_level_columns(data, columns, filters)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	chart = get_chart_data(filters, columns, income, expense, net_profit_loss, currency)

	report_summary, primitive_summary = get_report_summary(
		period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	if filters.get("selected_view") == "Margin":
		compute_margin_view_data(data, period_list, filters.accumulated_values)

	return columns, data, None, chart, report_summary, primitive_summary


def add_level_columns(data, columns, filters):
	"""Add ancestor level columns, is_group column, and optionally filter out group accounts."""
	if not data:
		return data, columns

	# Build accounts_by_name lookup from the company's chart of accounts
	company = filters.company
	all_accounts = frappe.db.sql(
		"""select name, parent_account, is_group from `tabAccount` where company=%s""",
		company,
		as_dict=True,
	)
	accounts_by_name = {a.name: a for a in all_accounts}

	# Build parent_children_map for is_group detection
	parent_children_map = {}
	for a in all_accounts:
		parent_children_map.setdefault(a.parent_account or None, []).append(a)

	max_depth = 0
	processed_data = []

	for row in data:
		account = row.get("account", "")
		# Skip special rows (totals, blank rows, net profit, etc.)
		if not account or account.startswith("'") or account not in accounts_by_name:
			processed_data.append(row)
			continue

		# Determine is_group
		is_group = bool(parent_children_map.get(account))
		row["is_group"] = is_group

		# Skip group accounts if filter is set
		if filters.get("hide_group_accounts") and is_group:
			continue

		# Walk the full ancestor chain
		ancestors = []
		current = accounts_by_name.get(account, {}).get("parent_account")
		while current and current in accounts_by_name:
			ancestors.append(current)
			current = accounts_by_name[current].parent_account

		# Reverse so that level 1 = root, level 2 = child of root, etc.
		ancestors.reverse()
		for i, ancestor in enumerate(ancestors, start=1):
			row[f"parent_account_{i}"] = ancestor

		if len(ancestors) > max_depth:
			max_depth = len(ancestors)

		processed_data.append(row)

	# Second pass: fill blank level columns by copying the previous level
	for row in processed_data:
		account = row.get("account", "")
		if not account or account.startswith("'"):
			continue
		for i in range(1, max_depth + 1):
			if not row.get(f"parent_account_{i}"):
				row[f"parent_account_{i}"] = row.get(f"parent_account_{i - 1}") if i > 1 else row.get("account", "")

	# Rebuild columns: Level columns + Account + Is Group + rest of original columns
	level_columns = []
	for i in range(1, max_depth + 1):
		level_columns.append({
			"fieldname": f"parent_account_{i}",
			"label": _("Level {0}").format(i),
			"fieldtype": "Link",
			"options": "Account",
			"width": 200,
		})

	# Original columns: account is first, then currency (hidden), then period columns
	account_col = columns[0]  # the Account column
	is_group_col = {
		"fieldname": "is_group",
		"label": _("Is Group"),
		"fieldtype": "Check",
		"width": 80,
	}
	rest_columns = columns[1:]  # currency + period columns

	new_columns = level_columns + [account_col, is_group_col] + rest_columns

	return processed_data, new_columns


def get_report_summary(
	period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False
):
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	if filters.accumulated_values:
		# when 'accumulated_values' is enabled, periods have running balance.
		# so, last period will have the net amount.
		key = period_list[-1].key
		if income:
			net_income = income[-2].get(key)
		if expense:
			net_expense = expense[-2].get(key)
		if net_profit_loss:
			net_profit = net_profit_loss.get(key)
	else:
		for period in period_list:
			key = period if consolidated else period.key
			if income:
				net_income += income[-2].get(key)
			if expense:
				net_expense += expense[-2].get(key)
			if net_profit_loss:
				net_profit += net_profit_loss.get(key)

	if len(period_list) == 1 and periodicity == "Yearly":
		profit_label = _("Profit This Year")
		income_label = _("Total Income This Year")
		expense_label = _("Total Expense This Year")
	else:
		profit_label = _("Net Profit")
		income_label = _("Total Income")
		expense_label = _("Total Expense")

	return [
		{"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	], net_profit


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
	total = 0
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss


def get_chart_data(filters, columns, income, expense, net_profit_loss, currency):
	labels = [d.get("label") for d in columns[2:]]

	income_data, expense_data, net_profit = [], [], []

	for p in columns[2:]:
		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))

	datasets = []
	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit:
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"
	chart["options"] = "currency"
	chart["currency"] = currency

	return chart

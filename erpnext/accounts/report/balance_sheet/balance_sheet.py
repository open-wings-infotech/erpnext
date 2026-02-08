# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.accounts.report.financial_statements import (
	compute_growth_view_data,
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

	filters.period_start_date = period_list[0]["year_start_date"]

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	asset = get_data(
		filters.company,
		"Asset",
		"Debit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	liability = get_data(
		filters.company,
		"Liability",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	equity = get_data(
		filters.company,
		"Equity",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
	)

	provisional_profit_loss, total_credit = get_provisional_profit_loss(
		asset, liability, equity, period_list, filters.company, currency
	)

	message, opening_balance = check_opening_balance(asset, liability, equity)

	data = []
	data.extend(asset or [])
	data.extend(liability or [])
	data.extend(equity or [])
	if opening_balance and round(opening_balance, 2) != 0:
		unclosed = {
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		for period in period_list:
			unclosed[period.key] = opening_balance
			if provisional_profit_loss:
				provisional_profit_loss[period.key] = provisional_profit_loss[period.key] - opening_balance

		unclosed["total"] = opening_balance
		data.append(unclosed)

	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	if total_credit:
		data.append(total_credit)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, company=filters.company
	)

	# Post-process: add ancestor level columns and is_group
	data, columns = add_level_columns(data, columns, filters)

	chart = get_chart_data(filters, columns, asset, liability, equity, currency)

	report_summary, primitive_summary = get_report_summary(
		period_list, asset, liability, equity, provisional_profit_loss, currency, filters
	)

	if filters.get("selected_view") == "Growth":
		compute_growth_view_data(data, period_list)

	return columns, data, message, chart, report_summary, primitive_summary


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
		# Skip special rows (totals, blank rows, provisional P&L, etc.)
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


def get_provisional_profit_loss(
	asset, liability, equity, period_list, company, currency=None, consolidated=False
):
	provisional_profit_loss = {}
	total_row = {}
	if asset:
		total = total_row_total = 0
		currency = currency or frappe.get_cached_value("Company", company, "default_currency")
		total_row = {
			"account_name": "'" + _("Total (Credit)") + "'",
			"account": "'" + _("Total (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		has_value = False

		for period in period_list:
			key = period if consolidated else period.key
			total_assets = flt(asset[-2].get(key))
			effective_liability = 0.00

			if liability and liability[-1] == {}:
				effective_liability += flt(liability[-2].get(key))
			if equity and equity[-1] == {}:
				effective_liability += flt(equity[-2].get(key))

			provisional_profit_loss[key] = total_assets - effective_liability
			total_row[key] = provisional_profit_loss[key] + effective_liability

			if provisional_profit_loss[key]:
				has_value = True

			total += flt(provisional_profit_loss[key])
			provisional_profit_loss["total"] = total

			total_row_total += flt(total_row[key])
			total_row["total"] = total_row_total

		if has_value:
			provisional_profit_loss.update(
				{
					"account_name": "'" + _("Provisional Profit / Loss (Credit)") + "'",
					"account": "'" + _("Provisional Profit / Loss (Credit)") + "'",
					"warn_if_negative": True,
					"currency": currency,
				}
			)

	return provisional_profit_loss, total_row


def check_opening_balance(asset, liability, equity):
	# Check if previous year balance sheet closed
	opening_balance = 0
	float_precision = cint(frappe.db.get_default("float_precision")) or 2
	if asset:
		opening_balance = flt(asset[-1].get("opening_balance", 0), float_precision)
	if liability:
		opening_balance -= flt(liability[-1].get("opening_balance", 0), float_precision)
	if equity:
		opening_balance -= flt(equity[-1].get("opening_balance", 0), float_precision)

	opening_balance = flt(opening_balance, float_precision)
	if opening_balance:
		return _("Previous Financial Year is not closed"), opening_balance
	return None, None


def get_report_summary(
	period_list,
	asset,
	liability,
	equity,
	provisional_profit_loss,
	currency,
	filters,
	consolidated=False,
):
	net_asset, net_liability, net_equity, net_provisional_profit_loss = 0.0, 0.0, 0.0, 0.0

	if filters.get("accumulated_values"):
		period_list = [period_list[-1]]

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for period in period_list:
		key = period if consolidated else period.key
		if asset:
			net_asset += asset[-2].get(key)
		if liability and liability[-1] == {}:
			net_liability += liability[-2].get(key)
		if equity and equity[-1] == {}:
			net_equity += equity[-2].get(key)
		if provisional_profit_loss:
			net_provisional_profit_loss += provisional_profit_loss.get(key)

	return [
		{"value": net_asset, "label": _("Total Asset"), "datatype": "Currency", "currency": currency},
		{
			"value": net_liability,
			"label": _("Total Liability"),
			"datatype": "Currency",
			"currency": currency,
		},
		{"value": net_equity, "label": _("Total Equity"), "datatype": "Currency", "currency": currency},
		{
			"value": net_provisional_profit_loss,
			"label": _("Provisional Profit / Loss (Credit)"),
			"indicator": "Green" if net_provisional_profit_loss > 0 else "Red",
			"datatype": "Currency",
			"currency": currency,
		},
	], (net_asset - net_liability + net_equity)


def get_chart_data(filters, columns, asset, liability, equity, currency):
	labels = [d.get("label") for d in columns[2:]]

	asset_data, liability_data, equity_data = [], [], []

	for p in columns[2:]:
		if asset:
			asset_data.append(asset[-2].get(p.get("fieldname")))
		if liability:
			liability_data.append(liability[-2].get(p.get("fieldname")))
		if equity:
			equity_data.append(equity[-2].get(p.get("fieldname")))

	datasets = []
	if asset_data:
		datasets.append({"name": _("Assets"), "values": asset_data})
	if liability_data:
		datasets.append({"name": _("Liabilities"), "values": liability_data})
	if equity_data:
		datasets.append({"name": _("Equity"), "values": equity_data})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"
	chart["options"] = "currency"
	chart["currency"] = currency

	return chart

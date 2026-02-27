# AI Instructions: Replicate Financial Report Customizations

> **Context**: These instructions are for GitHub Copilot / AI assistant. After upgrading ERPNext to a newer version, feed this file to the AI and ask it to apply these changes on top of the fresh code. The shared module `financial_statements.py` and `financial_statements.js` should NOT be modified — all changes are in the individual report files.

---

## Goal

Replace the default single "Account" column + indentation-based hierarchy in **Trial Balance**, **Balance Sheet**, and **Profit & Loss Statement** with:

1. **`is_group` column** — first column (Check type, 80px). Because it's first, Frappe DataTable renders the tree collapse/expand arrow in it. Set `display: block !important` on `.dt-tree-node` to keep it right-aligned (DataTable defaults to `display: flex` which breaks alignment).

2. **Level columns** (`level_1`, `level_2`, …) — dynamically generated based on the deepest account. Each account's name appears ONLY at its own depth column. No ancestor filling by default.

3. **New filters**:
   - `hide_group_accounts` (Check) — removes group/parent account rows, strips `indent` so tree degrades to flat
   - `fill_columns` (Check) — fills each row's ancestor level cells with parent names, cascades trailing blanks
   - `show_chart` (Check, default off) — chart hidden by default, generated only when checked

4. **Tree behavior preserved** — `indent` property stays in data rows for collapse/expand. The original `tree: true`, `parent_field: "parent_account"`, `initial_depth: 3` config is kept. `name_field` must be set to `"account"` (NOT `"is_group"` — the shared formatter replaces `name_field` column value with `account_name`, which would make every is_group cell truthy).

5. **Scoped CSS** — inject on report `onload`, remove on `page-change` when navigating away. This prevents breaking other tree reports (Cash Flow, Consolidated, etc.).

---

## File-by-file Instructions

### 1. `balance_sheet.py`

**In `execute()` function**, after `columns = get_columns(...)`:
- Save `chart_columns = columns[:]` (copy before modification)
- Call `data, columns = add_level_columns(data, columns, filters)`
- Change chart line to: `chart = get_chart_data(filters, chart_columns, ...) if filters.get("show_chart") else None`

**Add new function `add_level_columns(data, columns, filters)`:**
- Query all accounts: `select name, account_name, parent_account, is_group from tabAccount where company=%s`
- Build `accounts_by_name` dict
- For each data row:
  - Skip special rows (empty account, account starts with `'`, not in accounts_by_name). For these, strip quotes from label and put in `level_1`
  - Set `row["is_group"] = acc_info.is_group` (from DB, NOT computed from parent_children_map)
  - If `hide_group_accounts` filter and is_group: skip row
  - Walk ancestor chain (parent_account → grandparent → …), reverse to root-first
  - `level = len(ancestors) + 1`, set `row[f"level_{level}"] = row.get("account_name") or account`
  - Track `max_depth`, store `_level` and `_ancestors` on row for fill pass
- Fill columns pass (if `fill_columns` filter):
  - Fill ancestor levels: for each ancestor, get `account_name` from `accounts_by_name`
  - Fill trailing blanks: copy previous level value rightward
- Else: clean up `_level` and `_ancestors` from rows
- If `hide_group_accounts`: remove `indent` from all rows
- Build column list: `[is_group_col] + level_columns + rest_columns` (rest = original columns minus first Account column)

### 2. `balance_sheet.js`

**Add 3 new filters** to the `.push()` call (after existing ones):
- `hide_group_accounts` (Check)
- `fill_columns` (Check)
- `show_chart` (Check)

**Add scoped CSS** (NOT global, NOT at module load):
```js
let _bs_style_id = "bs-tree-no-indent-style";
function _bs_inject_css() {
    // Create <style> with:
    // .dt-tree-node[style] { padding-left: 0 !important; display: block !important; }
    // .dt-tree-node__toggle[style] { left: 0 !important; }
}
function _bs_remove_css() { /* remove element by id */ }
```
**Override `onload`**: wrap the existing onload, call `_bs_inject_css()`, bind `page-change` event to call `_bs_remove_css()` when route is no longer `query-report/Balance Sheet`.

**Override `formatter`**: wrap the existing formatter. For columns where `fieldname` starts with `"level_"` or equals `"is_group"`:
- Add `link_onclick` for General Ledger on level columns with values
- Use `default_formatter` (skip growth/margin formatting)
- Bold for rows without `parent_account`
- For all other columns, delegate to original formatter

### 3. `trial_balance.py`

**In `execute()`**: change return to `columns, data` where `get_data` returns `(data, max_depth)` and `get_columns(max_depth)` builds dynamic columns.

**Rewrite `prepare_data()`** to accept `accounts_by_name` parameter:
- For each account `d`:
  - `is_group = d.is_group` (from DB record, NOT `bool(parent_children_map.get(d.name))`)
  - Skip if `hide_group_accounts` and is_group
  - Build row with `is_group`, `account`, `parent_account`, `indent`, `account_name` (with account_number prefix if exists)
  - Walk ancestor chain, compute level, set `row[f"level_{level}"] = row["account_name"]`
  - Store `_level`, `_ancestors` for fill pass
- Fill columns pass (same logic as balance_sheet, but use `account_number - account_name` format for ancestors too)
- If `hide_group_accounts`: remove indent from all rows
- Total row: strip quotes from label, put in `level_1`
- Return `data, max_depth`

**Rewrite `get_columns(max_depth=0)`**:
- Start with `is_group` column (Check, 80px)
- Dynamic `level_1` through `level_{max_depth}` columns (Data, 200px)
- Then the standard currency + value columns (opening_debit, opening_credit, debit, credit, closing_debit, closing_credit)

### 4. `trial_balance.js`

**Keep tree config** but set `name_field: "account"` (NOT `"is_group"`):
```js
tree: true,
name_field: "account",
parent_field: "parent_account",
initial_depth: 3,
```

**Add filters**: `hide_group_accounts`, `fill_columns` (at the end of the filters array)

**Add scoped CSS** (same pattern as balance_sheet, unique id `"tb-tree-no-indent-style"`, page-change check for `"query-report/Trial Balance"`)

**Use** `erpnext.financial_statements.formatter` as the formatter (no custom override needed since Trial Balance doesn't have Growth/Margin views that interfere with level columns)

### 5. `general_ledger.py`

**In `get_conditions()` function**, BEFORE the existing `if filters.get("account"):` block:
- Add `parent_account` filter expansion:
  - Get `lft`, `rgt` from the selected parent account
  - Query all descendant accounts: `select name from tabAccount where lft >= %s and rgt <= %s`
  - If `account` filter also set, intersect the two lists (keep only accounts that are both descendants of parent AND in the account filter)
  - Otherwise, set `filters.account = child_accounts`

**In `execute()` function**, after `res = get_result(filters, account_details)`:
- Add: `if filters.get("show_account_levels"): res, columns = add_level_columns(res, columns, filters)`

**Add new function `add_level_columns(data, columns, filters)`** (before `get_accounts_with_children`):
- Query all accounts: `select name, account_name, parent_account, is_group from tabAccount where company=%s`
- Build `accounts_by_name` dict
- For each data row:
  - Get `account` field; skip rows without account or not in accounts_by_name
  - Walk ancestor chain (parent_account → grandparent → …), reverse to root-first
  - `level = len(ancestors) + 1`
  - Fill `row[f"level_{i}"]` with ancestor account_name for each ancestor
  - Place account's own account_name at `row[f"level_{level}"]`
  - Track `max_depth`
- Build level columns (`level_1` through `level_{max_depth}`, Data type, 180px width)
- Insert level columns after the Account column in the column list
- Return `data, new_columns`

### 6. `general_ledger.js`

**Add `parent_account` filter** after the existing `account` filter:
- fieldtype: Link, options: Account
- `get_query`: filter to `is_group: 1` and current company

**Add `show_account_levels` filter** at end of filters array:
- fieldtype: Check, label: "Show Account Hierarchy"

**Note**: General Ledger is NOT a tree report — no scoped CSS, tree config, or formatter override needed.

### 7. `profit_and_loss_statement.py`

Identical pattern to `balance_sheet.py`:
- Save `chart_columns` before processing
- Add `add_level_columns()` function (same logic as balance_sheet version)
- Conditional chart: `if filters.get("show_chart") else None`

### 8. `profit_and_loss_statement.js`

Identical pattern to `balance_sheet.js`:
- Add 3 filters: `hide_group_accounts`, `fill_columns`, `show_chart`
- Scoped CSS with unique id `"pl-tree-no-indent-style"`, page-change check for `"query-report/Profit and Loss Statement"`
- Formatter override (same as balance_sheet — intercept level_ and is_group columns, delegate rest to original)

---

## Critical Gotchas

1. **`name_field` must be `"account"`** — NOT `"is_group"`. The shared `financial_statements.js` formatter replaces the `name_field` column's value with `data.account_name`. If `name_field` is `"is_group"`, every is_group cell shows a truthy string → all checkboxes appear ticked.

2. **`is_group` must come from `d.is_group`** (the Account table's DB field) — NOT computed as `bool(parent_children_map.get(d.name))`. The parent_children_map approach incorrectly marks every non-leaf account as a group.

3. **CSS must be scoped** — inject on onload, remove on page-change. Global CSS breaks tree indentation in Cash Flow, Consolidated Financial Statement, Gross/Net Profit, and Dimension-Wise reports.

4. **`display: block !important`** on `.dt-tree-node` — required to override DataTable's `display: flex` which breaks the Check column's right-alignment.

5. **Chart columns** — save a copy of original columns BEFORE `add_level_columns()`. The chart function expects period columns, not level columns.

6. **Special rows** (totals, provisional P&L, net profit) have account names wrapped in single quotes like `'Total Asset (Debit)'`. Strip the quotes before putting in `level_1`.

7. **`financial_statements.py` and `financial_statements.js`** — do NOT modify. All changes are post-processing in individual report files.

---

## Files Changed (for .customized-files tracking)

```
erpnext/accounts/report/trial_balance/trial_balance.js
erpnext/accounts/report/trial_balance/trial_balance.py
erpnext/accounts/report/balance_sheet/balance_sheet.js
erpnext/accounts/report/balance_sheet/balance_sheet.py
erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.js
erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.py
erpnext/accounts/report/general_ledger/general_ledger.js
erpnext/accounts/report/general_ledger/general_ledger.py
open_wings/customizations.md
open_wings/customizations-ai.md
```

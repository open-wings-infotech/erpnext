# Open Wings — ERPNext Customizations

## Balance Sheet Report

**Files changed:**
- `erpnext/accounts/report/balance_sheet/balance_sheet.py`
- `erpnext/accounts/report/balance_sheet/balance_sheet.js`

**What changed:**

Default ERPNext shows the account hierarchy in a single "Account" column using indentation (padding-left). We replaced that with **multiple Level columns** (`Level 1`, `Level 2`, …) — one per depth in the chart of accounts. Each account name appears only in its own depth column.

The collapse/expand **tree arrow moved to a new `Is Group` column** (first column, right-aligned). Tree collapse/expand still works via Frappe's standard `indent` mechanism — `financial_statements.py` is NOT modified.

**New filters added:**
- **Hide Group Accounts** — removes parent/group rows, flattens the list
- **Fill Columns** — fills blank level cells with ancestor names (parent, grandparent, etc.) and cascades trailing blanks
- **Show Chart** — chart hidden by default, opt-in

**How it works:**
- `add_level_columns()` in `balance_sheet.py` post-processes data/columns from the shared `financial_statements` module
- CSS in `balance_sheet.js` overrides DataTable's inline indent styles (`padding-left: 0`, `display: block`) since hierarchy is shown via columns not spacing
- Custom formatter skips Growth/Margin formatting on level columns and adds General Ledger links

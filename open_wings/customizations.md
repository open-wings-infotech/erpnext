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

---

## General Ledger Report

**Files changed:**
- `erpnext/accounts/report/general_ledger/general_ledger.py`
- `erpnext/accounts/report/general_ledger/general_ledger.js`

**What changed:**

Added **account hierarchy level columns** and a **Parent Account filter** to the General Ledger report.

**New filters added:**
- **Parent Account** — Link field filtered to group accounts only. Selecting a parent account automatically fetches all sub-group/child accounts using the nested set (lft/rgt) model. Works in combination with the existing Account filter (intersection if both set).
- **Show Account Hierarchy** — Check field. When enabled, adds dynamic Level columns (`Level 1`, `Level 2`, …) after the Account column showing the full account hierarchy from root to the account itself.

**How it works:**
- `parent_account` filter in `get_conditions()` expands to all descendant accounts via `lft/rgt` SQL query, then merges with any existing `account` filter
- `add_level_columns()` in `general_ledger.py` queries all accounts for the company, walks ancestor chain for each GL entry row, and fills level columns (root first). Level columns are inserted after the Account column.
- Unlike Balance Sheet/Trial Balance/P&L, General Ledger is NOT a tree report — no scoped CSS or tree config needed

---

## Payment Entry — Clear Clearance Date on Cancel

**Files changed:**
- `erpnext/accounts/doctype/payment_entry/payment_entry.py`

**What changed:**

When a Payment Entry is cancelled, the linked Bank Transaction is unlinked but the `clearance_date` was NOT cleared. When the cancelled Payment Entry is then amended, the `clearance_date` gets copied to the new draft (Frappe's amend intentionally copies `no_copy` fields). This causes the amended Payment Entry to not appear in Bank Reconciliation.

**Fix:** Added `self.db_set("clearance_date", None)` at the end of `on_cancel()` so the clearance date is cleared when cancelling, ensuring the amended entry starts clean.

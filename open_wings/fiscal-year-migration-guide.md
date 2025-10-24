# Fiscal Year Migration Guide
## Universal Guide for Fiscal Year Structure Changes

**Date:** October 24, 2025  
**Purpose:** Update GL Entry fiscal_year field to match new fiscal year structure

---

## Overview

This guide provides two approaches:

1. **Quick Guide (Live Mode)** - Bare minimum steps, direct execution (recommended if you've tested before)
2. **Detailed Guide (Safe Mode)** - Includes preview and dry-run steps (recommended for first-time use)

**Use Cases:**
- Switching from Apr-Mar to Jan-Dec fiscal years
- Changing from Jul-Jun to Jan-Dec fiscal years
- Any other fiscal year structure change
- Correcting fiscal_year field after creating new fiscal years

**How it works:**
The script uses ERPNext's `get_fiscal_year(posting_date, company)` function to automatically determine the correct fiscal year for each GL Entry based on its posting_date. You just need to create the new fiscal years first, and the script will update all records accordingly.

---
---

# Quick Migration Guide (Live Mode Only)
## Bare Minimum Steps - Direct Execution

⚠️ **WARNING:** This guide skips preview and dry-run steps. Use only if you're confident or have already tested the script.

---

## Prerequisites (CRITICAL)

### 1. Backup Database
```bash
cd /workspace/development/frappe-bench
bench --site [your-site-name] backup --with-files
```

### 2. Create Fiscal Years

In ERPNext UI:
- **Accounting > Setup > Fiscal Year > New**
- Create all fiscal years needed to cover your GL entry date ranges
- Examples:
  - Calendar Year: `JAN 2024 – DEC 2024` (2024-01-01 to 2024-12-31)
  - Financial Year: `APR 2024 – MAR 2025` (2024-04-01 to 2025-03-31)
  - Mid-year: `JUL 2024 – JUN 2025` (2024-07-01 to 2025-06-30)
- **Add your company to each fiscal year** in the Companies table

**Tip:** Check your GL entry date range first:
```sql
SELECT MIN(posting_date), MAX(posting_date) 
FROM `tabGL Entry` 
WHERE company = 'Your Company'
```
Then create fiscal years to cover this entire range.

---

## Execution Steps

### Step 1: Open Console
```bash
cd /workspace/development/frappe-bench
bench --site [your-site-name] console
```

### Step 2: Load the Migration Function

**IMPORTANT:** Copy and paste this entire block as one unit:

```python
import frappe

def update_fiscal_year_quick(company_name, debug=True, clear_cache=True):
    """Quick update of fiscal_year in GL Entry table - Live Mode"""
    # Import inside function to ensure it's always available
    from erpnext.accounts.utils import get_fiscal_year
    
    # Clear fiscal year cache to ensure fresh calculation
    if clear_cache:
        frappe.cache.delete_keys("fiscal_years")
        if debug:
            print("Cache cleared for fresh fiscal year calculation\n")
    
    print(f"\n{'='*60}")
    print(f"Updating Fiscal Year for: {company_name}")
    print(f"{'='*60}\n")
    
    gl_entries = frappe.get_all(
        "GL Entry",
        filters={"company": company_name},
        fields=["name", "posting_date", "fiscal_year"]
    )
    
    print(f"Total GL Entries: {len(gl_entries)}")
    print("Processing...\n")
    
    updated_count = 0
    errors = []
    
    for i, gl in enumerate(gl_entries, 1):
        try:
            correct_fy = get_fiscal_year(gl.posting_date, company=company_name)[0]
            
            if debug:
                print(f"Entry {i}: {gl.name}")
                print(f"  Posting Date: {gl.posting_date}")
                print(f"  Current FY: {gl.fiscal_year}")
                print(f"  Correct FY: {correct_fy}")
            
            if gl.fiscal_year != correct_fy:
                if debug:
                    print(f"  ⚠️  MISMATCH - Updating...")
                frappe.db.set_value(
                    "GL Entry",
                    gl.name,
                    "fiscal_year",
                    correct_fy,
                    update_modified=False
                )
                updated_count += 1
            else:
                if debug:
                    print(f"  ✓ Already correct")
            
            if debug:
                print()
            
            if i % 100 == 0:
                print(f"  {i}/{len(gl_entries)} processed...")
                
        except Exception as e:
            errors.append(f"{gl.name}: {str(e)}")
            if debug:
                print(f"  ❌ ERROR: {str(e)}\n")
    
    # Commit changes
    frappe.db.commit()
    
    print(f"\n{'='*60}")
    print(f"✅ COMPLETE")
    print(f"{'='*60}")
    print(f"Updated: {updated_count} records")
    if errors:
        print(f"Errors: {len(errors)}")
        for err in errors[:5]:
            print(f"  {err}")
    print(f"{'='*60}\n")
    
    # Verification
    result = frappe.db.sql("""
        SELECT fiscal_year, COUNT(*) as count
        FROM `tabGL Entry`
        WHERE company = %s
        GROUP BY fiscal_year
        ORDER BY fiscal_year
    """, (company_name,), as_dict=1)
    
    print("Fiscal Year Distribution:")
    for row in result:
        print(f"  {row.fiscal_year}: {row.count} entries")
    print()

# Function loaded and ready
print("\n✅ Quick Migration Function Loaded!")
print("Usage: update_fiscal_year_quick('Your Company Name')")
```

Press **Enter** after pasting. You should see:
```
✅ Quick Migration Function Loaded!
Usage: update_fiscal_year_quick('Your Company Name')
```

---

### Step 3: Run the Function

Replace `Your Company Name` with your actual company name:

```python
update_fiscal_year_quick("Your Company Name")
```

The function will execute and show progress.

---

### Step 4: Exit
```python
exit()
```

---

## Post-Execution

1. **Verify Reports** in ERPNext:
   - Trial Balance (for each fiscal year)
   - Profit & Loss Statement
   - General Ledger

2. **Check distribution**: Verify the output shows all your fiscal years with expected entry counts

3. **Test new transactions**: Create a test transaction (e.g., Journal Entry) and verify it automatically picks up the correct fiscal year based on posting date

---

## If Something Goes Wrong

Restore from backup:
```bash
cd /workspace/development/frappe-bench
bench --site [your-site-name] --force restore [backup-file-path]
```

---

**⚡ Total Time:** ~2-5 minutes (depending on number of GL entries)

---
---

# Detailed Migration Guide (Safe Mode)
## Complete Guide with Preview and Dry-Run Steps

This guide includes preview and dry-run steps for safe execution.

---

## ⚠️ Prerequisites

### 1. Backup Your Database
```bash
cd /workspace/development/frappe-bench
bench --site [your-site-name] backup --with-files
```

Replace `[your-site-name]` with your actual site name (e.g., `hub.localhost`)

### 2. Create New Fiscal Years

1. Login to ERPNext
2. Go to: **Accounting > Setup > Fiscal Year**
3. Create your new fiscal year(s) based on your requirement

**Examples:**

**Example 1: Switching to Jan-Dec (Calendar Year)**
- **Name:** `JAN 2024 – DEC 2024`
- **Year Start Date:** `2024-01-01`
- **Year End Date:** `2024-12-31`
- Add your company in the Companies table
- Save

Repeat for each year you need (e.g., JAN 2025 – DEC 2025, etc.)

**Example 2: Switching to Jul-Jun (Financial Year)**
- **Name:** `JUL 2024 – JUN 2025`
- **Year Start Date:** `2024-07-01`
- **Year End Date:** `2025-06-30`
- Add your company in the Companies table
- Save

**Example 3: Keeping Apr-Mar but fixing data**
- **Name:** `APR 2024 – MAR 2025`
- **Year Start Date:** `2024-04-01`
- **Year End Date:** `2025-03-31`
- Add your company in the Companies table
- Save

**Important Notes:**
- Create fiscal years that cover the date range of your existing GL entries
- The script will automatically assign each GL entry to the correct fiscal year based on its posting_date
- You can create multiple fiscal years at once before running the script
- Old fiscal years can remain in the system (they won't be deleted)
- Ensure your company is added to each new fiscal year

---

## 📝 Migration Script

### Step 1: Open Bench Console

```bash
cd /workspace/development/frappe-bench
bench --site [your-site-name] console
```

You should see a Python prompt: `>>>`

---

### Step 2: Copy and Paste the Complete Script

Copy this entire script and paste it into the console:

```python
import frappe

def preview_fiscal_year_changes(company_name, clear_cache=True):
    """Preview what will change before making updates"""
    # Import inside function to ensure it's always available
    from erpnext.accounts.utils import get_fiscal_year
    
    # Clear fiscal year cache to ensure fresh calculation
    if clear_cache:
        frappe.cache.delete_keys("fiscal_years")
        print("Cache cleared for fresh fiscal year calculation\n")
    
    print(f"\n{'='*60}")
    print(f"PREVIEW MODE - Company: {company_name}")
    print(f"{'='*60}\n")
    
    gl_entries = frappe.get_all(
        "GL Entry",
        filters={"company": company_name},
        fields=["name", "posting_date", "fiscal_year"],
        order_by="posting_date"
    )
    
    changes = []
    fy_distribution = {}
    
    for gl in gl_entries:
        try:
            correct_fy = get_fiscal_year(gl.posting_date, company=company_name)[0]
            
            # Track distribution
            fy_distribution[correct_fy] = fy_distribution.get(correct_fy, 0) + 1
            
            if gl.fiscal_year != correct_fy:
                changes.append({
                    "name": gl.name,
                    "posting_date": gl.posting_date,
                    "current_fy": gl.fiscal_year,
                    "new_fy": correct_fy
                })
        except Exception as e:
            print(f"⚠️  Error for GL Entry {gl.name}: {str(e)}")
    
    # Print summary
    print(f"Total GL Entries: {len(gl_entries)}")
    print(f"Records needing update: {len(changes)}\n")
    
    print("Distribution by Fiscal Year (after update):")
    for fy, count in sorted(fy_distribution.items()):
        print(f"  {fy}: {count} entries")
    
    if changes:
        print(f"\nSample changes (first 10):")
        print(f"{'GL Entry':<20} {'Date':<12} {'Current FY':<25} {'New FY'}")
        print(f"{'-'*80}")
        for change in changes[:10]:
            print(f"{change['name']:<20} {str(change['posting_date']):<12} {change['current_fy']:<25} {change['new_fy']}")
        
        if len(changes) > 10:
            print(f"\n... and {len(changes) - 10} more changes")
    
    print(f"\n{'='*60}\n")
    return changes


def update_gl_fiscal_year(company_name, dry_run=True, clear_cache=True):
    """Update fiscal_year in GL Entry table"""
    # Import inside function to ensure it's always available
    from erpnext.accounts.utils import get_fiscal_year
    
    # Clear fiscal year cache to ensure fresh calculation
    if clear_cache:
        frappe.cache.delete_keys("fiscal_years")
    
    if dry_run:
        print(f"\n{'='*60}")
        print("🔍 DRY RUN MODE - No changes will be committed")
        if clear_cache:
            print("Cache cleared for fresh fiscal year calculation")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print("⚠️  LIVE MODE - Changes will be committed to database")
        print(f"{'='*60}\n")
        response = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
        if response != "YES":
            print("❌ Operation cancelled.")
            return
    
    gl_entries = frappe.get_all(
        "GL Entry",
        filters={"company": company_name},
        fields=["name", "posting_date", "fiscal_year"]
    )
    
    updated_count = 0
    errors = []
    
    print("Processing GL Entries...")
    for i, gl in enumerate(gl_entries, 1):
        try:
            correct_fy = get_fiscal_year(gl.posting_date, company=company_name)[0]
            
            if gl.fiscal_year != correct_fy:
                if not dry_run:
                    frappe.db.set_value(
                        "GL Entry",
                        gl.name,
                        "fiscal_year",
                        correct_fy,
                        update_modified=False  # Don't update 'modified' timestamp
                    )
                updated_count += 1
            
            # Progress indicator every 100 records
            if i % 100 == 0:
                print(f"  Processed {i}/{len(gl_entries)} records...")
                
        except Exception as e:
            errors.append(f"GL Entry {gl.name}: {str(e)}")
    
    if not dry_run and updated_count > 0:
        frappe.db.commit()
        print(f"\n✅ Successfully updated {updated_count} GL Entry records")
    elif dry_run:
        print(f"\n📊 Would update {updated_count} GL Entry records")
    else:
        print(f"\n✓ No updates needed - all records already have correct fiscal year")
    
    if errors:
        print(f"\n❌ Errors encountered: {len(errors)}")
        for error in errors[:5]:
            print(f"  {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    
    print(f"\n{'='*60}\n")


def verify_fiscal_year_update(company_name, clear_cache=True):
    """Verify the fiscal year distribution after update"""
    # Clear fiscal year cache to ensure fresh calculation
    if clear_cache:
        frappe.cache.delete_keys("fiscal_years")
    
    print(f"\n{'='*60}")
    print(f"VERIFICATION - Company: {company_name}")
    if clear_cache:
        print("Cache cleared for fresh verification")
    print(f"{'='*60}\n")
    
    # Get distribution by fiscal year
    result = frappe.db.sql("""
        SELECT 
            fiscal_year,
            COUNT(*) as count,
            MIN(posting_date) as first_date,
            MAX(posting_date) as last_date
        FROM `tabGL Entry`
        WHERE company = %s
        GROUP BY fiscal_year
        ORDER BY fiscal_year
    """, (company_name,), as_dict=1)
    
    if result:
        print(f"{'Fiscal Year':<30} {'Count':<10} {'First Date':<15} {'Last Date'}")
        print(f"{'-'*75}")
        for row in result:
            print(f"{row.fiscal_year:<30} {row.count:<10} {str(row.first_date):<15} {str(row.last_date)}")
    else:
        print("No GL Entries found")
    
    print(f"\n{'='*60}\n")


# Script is loaded and ready to use
print("\n✅ Fiscal Year Migration Script Loaded Successfully!\n")
print("Available functions:")
print("  1. preview_fiscal_year_changes(company_name, clear_cache=True)")
print("  2. update_gl_fiscal_year(company_name, dry_run=True, clear_cache=True)")
print("  3. verify_fiscal_year_update(company_name, clear_cache=True)")
print("\nOptional Parameters:")
print("  - clear_cache=True  : Clear fiscal year cache before execution (recommended)")
print("  - clear_cache=False : Keep cached fiscal year data (faster, but may use stale data)")
print("\nNext step: Run the preview function (see guide below)")
```

Press **Enter** after pasting. You should see:
```
✅ Fiscal Year Migration Script Loaded Successfully!
```

---

### Step 3: Preview Changes

Replace `Your Company Name` with your actual company name:

```python
company_name = "Your Company Name"
changes = preview_fiscal_year_changes(company_name)
```

**Note:** By default, this clears the fiscal year cache to ensure fresh calculations. If you want to use cached data for faster execution, use:
```python
changes = preview_fiscal_year_changes(company_name, clear_cache=False)
```

**Expected Output:**
- Total GL Entries count
- Number of records needing update
- Distribution by fiscal year (shows how entries will be distributed across all fiscal years)
- Sample changes

**Example Output:**
```
============================================================
PREVIEW MODE - Company: Hub Client
============================================================

Total GL Entries: 1250
Records needing update: 1250

Distribution by Fiscal Year (after update):
  JAN 2024 – DEC 2024: 850 entries
  JAN 2025 – DEC 2025: 400 entries

Sample changes (first 10):
GL Entry             Date         Current FY                New FY
--------------------------------------------------------------------------------
ACC-GLE-2024-00001   2024-01-15   APR 2023 – MAR 2024      JAN 2024 – DEC 2024
...
```

**What to check:**
- Do the fiscal years shown match the ones you created?
- Does the distribution make sense for your date ranges?
- Are there any error messages?

---

### Step 4: Dry Run (Test Mode)

This will simulate the update without making changes:

```python
update_gl_fiscal_year(company_name, dry_run=True)
```

**Note:** Cache clearing is enabled by default. The function will automatically clear the fiscal year cache to ensure accurate calculations.

**Expected Output:**
```
============================================================
🔍 DRY RUN MODE - No changes will be committed
Cache cleared for fresh fiscal year calculation
============================================================

Processing GL Entries...
  Processed 100/1250 records...
  Processed 200/1250 records...
  ...

📊 Would update 1250 GL Entry records
```

---

### Step 5: Run the Actual Update

⚠️ **IMPORTANT:** Only proceed if preview and dry run look correct!

```python
update_gl_fiscal_year(company_name, dry_run=False)
```

When prompted, type `YES` (in capitals) and press Enter:
```
Are you sure you want to proceed? Type 'YES' to confirm: YES
```

**Expected Output:**
```
============================================================
⚠️  LIVE MODE - Changes will be committed to database
============================================================

Processing GL Entries...
  Processed 100/1250 records...
  Processed 200/1250 records...
  ...

✅ Successfully updated 1250 GL Entry records
```

---

### Step 6: Verify the Update

```python
verify_fiscal_year_update(company_name)
```

**Note:** This also clears cache by default to ensure verification uses fresh data from the database.

**Expected Output:**
```
============================================================
VERIFICATION - Company: Hub Client
Cache cleared for fresh verification
============================================================

Fiscal Year                    Count      First Date      Last Date
---------------------------------------------------------------------------
JAN 2024 – DEC 2024           850        2024-01-01      2024-12-31
JAN 2025 – DEC 2025           400        2025-01-01      2025-10-24
```

**What to verify:**
- Each fiscal year shows the expected count of entries
- First Date and Last Date fall within the fiscal year's date range
- All your GL entries are accounted for (total count matches)

---

### Step 7: Manual Verification (Optional)

Check a few random GL entries:

```python
# Check 20 random GL entries
frappe.db.sql("""
    SELECT name, posting_date, fiscal_year 
    FROM `tabGL Entry` 
    WHERE company = %s
    ORDER BY posting_date 
    LIMIT 20
""", (company_name,), as_dict=1)
```

---

### Step 8: Exit Console

```python
exit()
```

Or press `Ctrl+D`

---

## 📊 Post-Migration Verification

### 1. Check Reports in ERPNext

Login to ERPNext and verify these reports:

1. **General Ledger**
   - Path: `Accounting > Reports > General Ledger`
   - Filter by your fiscal year date ranges
   - Verify fiscal year column shows the correct fiscal year for each entry

2. **Trial Balance**
   - Path: `Accounting > Reports > Trial Balance`
   - Run for each of your new fiscal years
   - Verify totals match expected values

3. **Profit and Loss Statement**
   - Path: `Accounting > Reports > Profit and Loss Statement`
   - Check each fiscal year separately
   - Verify period totals are correct

4. **Balance Sheet**
   - Path: `Accounting > Reports > Balance Sheet`
   - Check year-end balances for each fiscal year end date
   - Verify opening and closing balances

---

## 🔧 Troubleshooting

### Issue: "Company not found" error
**Solution:** Check exact company name
```python
# List all companies
frappe.get_all("Company", fields=["name"])
```

### Issue: "Fiscal Year does not exist" error
**Solution:** Make sure you created the fiscal years first (Step 2 in Prerequisites)
```python
# List all fiscal years
frappe.get_all("Fiscal Year", fields=["name", "year_start_date", "year_end_date"])
```

### Issue: Getting incorrect or cached fiscal year results
**Solution:** Clear the fiscal year cache manually
```python
# Clear cache and try again
frappe.cache.delete_keys("fiscal_years")
```
**Note:** All functions now clear cache by default (`clear_cache=True`), but if you explicitly set `clear_cache=False` and see issues, use the above command.

### Issue: Some GL entries not updating
**Solution:** Check if those dates fall outside defined fiscal year ranges
```python
# Find GL entries that don't match any fiscal year
frappe.db.sql("""
    SELECT posting_date, COUNT(*) as count
    FROM `tabGL Entry`
    WHERE company = %s
    GROUP BY posting_date
    ORDER BY posting_date
""", (company_name,), as_dict=1)
```
Then create fiscal years to cover those date ranges.

### Issue: Need to rollback changes
**Solution:** Restore from backup
```bash
cd /workspace/development/frappe-bench
bench --site [your-site-name] --force restore [backup-file]
```

---

## 📋 Quick Reference

### Complete Script Execution (Copy-Paste)

```python
# Replace with your actual company name
company_name = "Your Company Name"

# Step 1: Preview
changes = preview_fiscal_year_changes(company_name)

# Step 2: Dry run
update_gl_fiscal_year(company_name, dry_run=True)

# Step 3: Actual update (only after confirming above steps)
update_gl_fiscal_year(company_name, dry_run=False)
# Type 'YES' when prompted

# Step 4: Verify
verify_fiscal_year_update(company_name)
```

---

## ✅ Success Checklist

- [ ] Database backup created
- [ ] New fiscal years created to cover all GL entry dates
- [ ] Company added to all new fiscal years
- [ ] Preview shows expected distribution
- [ ] Dry run completed successfully
- [ ] Actual update completed successfully
- [ ] Verification shows correct fiscal year distribution
- [ ] All GL entry dates fall within a fiscal year (no errors)
- [ ] Reports show correct data
- [ ] Tested new transaction to verify fiscal year is auto-assigned correctly

---

## 📞 Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Review error messages carefully
3. Restore from backup if needed
4. Consult ERPNext documentation: https://docs.erpnext.com

---

**Document Version:** 1.0  
**Last Updated:** October 24, 2025

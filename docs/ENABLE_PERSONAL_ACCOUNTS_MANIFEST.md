# Enable Personal Microsoft Accounts via Manifest

## Problem

The new Azure Portal Authentication (Preview) interface doesn't show the option for "Accounts in any organizational directory and personal Microsoft accounts". You need to edit the Manifest directly.

---

## Solution: Edit Manifest

### Step 1: Open Manifest Editor

1. **Go to Azure Portal** → **Microsoft Entra ID** → **App registrations**
2. **Find your app**: "fieldforce-dashboard"
3. **Click on it** to open
4. **In the left sidebar**, click **"Manifest"**
   - It's under the "Manage" section

### Step 2: Find and Edit signInAudience

1. **In the Manifest editor**, you'll see JSON code
2. **Find this line** (around line 10-15):
   ```json
   "signInAudience": "AzureADMultipleOrgs"
   ```
3. **Change it to**:
   ```json
   "signInAudience": "AzureADandPersonalMicrosoftAccount"
   ```
4. **Click "Save"** at the top

### Step 3: Verify Change

After saving, you should see:
- ✅ Success notification
- ✅ The manifest shows the updated value

---

## Available signInAudience Values

```json
"AzureADMyOrg"                    // Single tenant only
"AzureADMultipleOrgs"             // Any organizational directory (current)
"AzureADandPersonalMicrosoftAccount"  // Organizational + Personal accounts (what you need)
"PersonalMicrosoftAccount"        // Personal accounts only
```

---

## What This Enables

After changing to `"AzureADandPersonalMicrosoftAccount"`:

✅ **Organizational accounts** from any Azure AD tenant
✅ **Personal Microsoft accounts** (@outlook.com, @hotmail.com, @live.com, etc.)
✅ **Custom domains** registered as personal accounts

---

## After Making the Change

1. **Wait 1-2 minutes** for changes to propagate
2. **Test login** with `sanjeev@dachido.com`
3. **Should work** now (if it's a personal Microsoft account)

---

## Important Notes

⚠️ **Warning from Azure**: They don't recommend enabling personal accounts for existing registrations due to "temporary differences in supported functionality", but it's still possible and will work.

⚠️ **Publisher Verification**: For multitenant apps, you may need to verify your publisher (add MPN ID) for better user experience.

---

## Troubleshooting

### Can't find Manifest?

- Look in the left sidebar under "Manage"
- It should be near the bottom of the Manage section
- If you don't see it, you might need different permissions

### Save button grayed out?

- Make sure you actually changed the value
- Check for JSON syntax errors (commas, quotes)
- Try refreshing the page

### Still getting errors after change?

1. Wait 2-3 minutes (changes can take time)
2. Clear browser cache
3. Try incognito/private window
4. Check the manifest saved correctly

---

## Quick Reference

**Current setting:**
```json
"signInAudience": "AzureADMultipleOrgs"
```

**Change to:**
```json
"signInAudience": "AzureADandPersonalMicrosoftAccount"
```

**Location:**
Azure Portal → App registrations → fieldforce-dashboard → Manifest



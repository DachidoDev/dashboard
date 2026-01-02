# Redirect URI Troubleshooting

## Error: "Must start with 'HTTPS' or 'http://localhost'"

Even with lowercase `https://`, you're getting this error. Here are solutions:

---

## Solution 1: Clear and Re-enter

1. **Delete the current URI** completely (trash icon)
2. **Click outside the field** to ensure it's cleared
3. **Click the empty field** again
4. **Type carefully** (don't copy-paste):
   ```
   https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback
   ```
5. **Check for spaces** - no leading/trailing spaces
6. **Click Save**

---

## Solution 2: Check for Hidden Characters

Sometimes copy-paste introduces hidden characters:

1. **Delete the URI**
2. **Type it manually** character by character:
   - `h` `t` `t` `p` `s` `:` `/` `/` 
   - `f` `i` `e` `l` `d` `f` `o` `r` `c` `e` `-` `d` `a` `s` `h` `b` `o` `a` `r` `d` `.` `a` `z` `u` `r` `e` `w` `e` `b` `s` `i` `t` `e` `s` `.` `n` `e` `t` `/` `.` `a` `u` `t` `h` `/` `l` `o` `g` `i` `n` `/` `a` `a` `d` `/` `c` `a` `l` `l` `b` `a` `c` `k`

---

## Solution 3: Use Azure Portal's Auto-Suggestion

1. **Delete current URI**
2. **Start typing**: `https://`
3. **Let Azure suggest** your app URL
4. **Complete the path**: `/.auth/login/aad/callback`

---

## Solution 4: Verify App Registration

Make sure you're editing the **correct** app registration:

1. **Check Client ID** matches: `6da24c1c-781a-45e3-b5f4-b539380616ab`
2. **Verify you're in the right tenant**
3. **Check you have permissions** to edit app registrations

---

## Solution 5: Try Alternative Method

If the Web platform isn't working, try:

1. **Delete the Web platform** (if it exists)
2. **Click "+ Add a platform"**
3. **Select "Web"**
4. **Add redirect URI** in the new platform configuration
5. **Check "ID tokens"**
6. **Save**

---

## Solution 6: Check Browser/Portal Issues

1. **Refresh the page** (F5)
2. **Try a different browser** (Chrome, Edge, Firefox)
3. **Clear browser cache**
4. **Try incognito/private window**
5. **Check if you have proper permissions** (Application Developer role)

---

## Exact Format Required

The redirect URI must be **exactly**:

```
https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback
```

**Checklist:**
- ✅ Starts with `https://` (lowercase)
- ✅ No spaces before or after
- ✅ No special characters
- ✅ Full domain: `fieldforce-dashboard.azurewebsites.net`
- ✅ Exact path: `/.auth/login/aad/callback`
- ✅ No trailing slash

---

## Alternative: Use Azure CLI

If the portal keeps giving errors, use Azure CLI:

```bash
az ad app update --id 6da24c1c-781a-45e3-b5f4-b539380616ab \
  --web-redirect-uris "https://fieldforce-dashboard.azurewebsites.net/.auth/login/aad/callback"
```

---

## Still Not Working?

1. **Check Azure Portal status** - might be a temporary issue
2. **Wait a few minutes** and try again
3. **Contact Azure support** if the issue persists
4. **Check Azure Service Health** for known issues

---

## Verification

After successfully adding the redirect URI:

1. **Refresh the Authentication page**
2. **Verify the URI appears** in the list
3. **Check it's under "Web" platform**
4. **Verify "ID tokens" is checked**
5. **Test the login flow**


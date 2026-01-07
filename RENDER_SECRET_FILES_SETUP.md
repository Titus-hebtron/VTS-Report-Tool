# Render Setup with Secret Files - VTS Backup

## ✅ Your Current Configuration

You're using **Render Secret Files** (the recommended approach):
- **Environment Variable:** `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/google_service_account.json`
- **Secret File:** `/etc/secrets/google_service_account.json` (contains your service account JSON)

This is the **best practice** approach and your code now fully supports it! ✅

---

## 🎯 How It Works

1. **Render Secret Files:**
   - You upload your service account JSON as a secret file
   - Render mounts it at `/etc/secrets/google_service_account.json`
   - This keeps credentials secure and separate from environment variables

2. **GOOGLE_APPLICATION_CREDENTIALS:**
   - This is the standard Google Cloud environment variable
   - It tells Google's authentication libraries where to find the credentials
   - Your backup scripts automatically detect and use it

3. **Authentication Priority:**
   ```
   1. GOOGLE_APPLICATION_CREDENTIALS (file path) ← YOU'RE USING THIS ✅
   2. GOOGLE_CREDENTIALS_JSON (inline JSON)
   3. AWS Secrets Manager
   4. Azure Key Vault
   5. Local credentials.json file (development)
   ```

---

## 📋 Verification Steps

### Step 1: Verify Your Render Configuration

1. **Check Secret Files:**
   - Go to Render Dashboard → Your Service → Environment
   - Scroll to **Secret Files** section
   - Verify: `/etc/secrets/google_service_account.json` exists

2. **Check Environment Variables:**
   - In same Environment page
   - Verify: `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/google_service_account.json`

### Step 2: Verify Service Account Permissions

1. **Open Google Drive**
   - Go to https://drive.google.com/

2. **Find VTS_Backups Folder**
   - Look for folder named **VTS_Backups**
   - If it doesn't exist, create it

3. **Check Sharing:**
   - Right-click **VTS_Backups** → Share
   - Verify your service account email is listed with **Editor** access
   - Service account email looks like: `vts-backup-service@vts-backup-tool.iam.gserviceaccount.com`
   
   **How to find service account email:**
   - Open your JSON key file (the one you uploaded to Render)
   - Look for `"client_email"` field

### Step 3: Test the Backup

1. **Deploy Your Service**
   - If you haven't already, click **Manual Deploy** on Render

2. **Run Test Backup**
   - Navigate to your VTS app
   - Go to **Backup Management** page
   - Click **☁️ Run Full Backup to Google Drive**

3. **Check Logs**
   - Monitor Render logs for:
     ```
     ✅ Service Account authentication successful
     Database backup created: backups/vts_database_backup_*.db
     Images backup created: backups/uploaded_images_backup_*.zip
     File uploaded to Google Drive: ...
     Email notification sent to hebtron25@gmail.com
     ```

4. **Verify in Google Drive**
   - Check **VTS_Backups** folder
   - Should contain:
     - `vts_database_backup_YYYYMMDD_HHMMSS.db`
     - `uploaded_images_backup_YYYYMMDD_HHMMSS.zip`

---

## 🔧 SMTP Configuration (Email Notifications)

You also need SMTP credentials configured. Add these to Render Environment Variables:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
```

**To get Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Create new app password for "VTS Backup"
3. Copy the 16-character password
4. Use it as `SMTP_PASSWORD`

---

## 🐛 Troubleshooting

### Issue: "Could not load credentials from file"

**Possible Causes:**
- Secret file not properly uploaded to Render
- Wrong file path in environment variable

**Solution:**
1. Go to Render Dashboard → Environment → Secret Files
2. Verify `/etc/secrets/google_service_account.json` exists
3. Re-upload if needed
4. Redeploy service

### Issue: "Service Account authentication failed"

**Possible Causes:**
- Invalid JSON in secret file
- Incorrect service account configuration

**Solution:**
1. Download a fresh service account key from Google Cloud Console
2. Re-upload to Render Secret Files
3. Verify JSON is valid (check for complete private key)

### Issue: "Access denied" or "Permission denied" on Google Drive

**Possible Causes:**
- VTS_Backups folder not shared with service account
- Service account doesn't have Editor permissions

**Solution:**
1. Open your service account JSON (local copy)
2. Find `"client_email"` value (e.g., `vts-backup-service@...`)
3. In Google Drive, share VTS_Backups folder with this email
4. Give **Editor** access
5. Wait 1-2 minutes for permissions to propagate

### Issue: "Email notification failed"

**Possible Causes:**
- SMTP credentials not configured
- Using regular Gmail password instead of App Password

**Solution:**
1. Verify all 4 SMTP environment variables are set
2. If using Gmail, generate and use an App Password
3. Enable 2FA on your Google account first

---

## 📊 Checking Logs

### View Real-Time Logs on Render:

1. Go to Render Dashboard
2. Click on your service
3. Click **Logs** tab
4. Look for:
   - `Service Account authentication successful`
   - `Database backup created`
   - `File uploaded to Google Drive`
   - `Email notification sent`

### Common Log Messages:

✅ **Success:**
```
INFO - Using Service Account authentication
INFO - ✅ Service Account authentication successful
INFO - Database backup created: backups/vts_database_backup_20260107_153045.db
INFO - File uploaded to Google Drive: ... (ID: 1abc...)
INFO - Email notification sent to hebtron25@gmail.com
```

❌ **Issues:**
```
WARNING - Service Account authentication failed: ...
ERROR - Could not load credentials from file: ...
ERROR - Permission denied accessing Google Drive
```

---

## ✅ Quick Checklist

Before running backups, verify:

- [ ] Secret File uploaded: `/etc/secrets/google_service_account.json`
- [ ] Environment Variable: `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/google_service_account.json`
- [ ] VTS_Backups folder created in Google Drive
- [ ] VTS_Backups folder shared with service account email (Editor access)
- [ ] SMTP credentials configured (4 environment variables)
- [ ] Service deployed on Render
- [ ] Test backup successful
- [ ] Files visible in Google Drive
- [ ] Email notification received

---

## 🚀 You're All Set!

Your configuration using Render Secret Files is the **recommended best practice**. Your backup system should now work seamlessly with:

✅ Secure credential storage (Secret Files)
✅ Automatic Google Drive uploads
✅ Email notifications
✅ Scheduled backups every 21 hours

**Next:** Just deploy and test! Everything is configured correctly.

---

## 📖 Related Documentation

- [BACKUP_SETUP_GUIDE.md](./BACKUP_SETUP_GUIDE.md) - Complete setup guide
- [BACKUP_CHANGES_SUMMARY.md](./BACKUP_CHANGES_SUMMARY.md) - What was changed
- [Render Secret Files Docs](https://render.com/docs/configure-environment-variables#secret-files)
- [Google Cloud Service Accounts](https://cloud.google.com/iam/docs/service-accounts)

---

**Last Updated:** 2026-01-07  
**Configuration:** Render Secret Files with GOOGLE_APPLICATION_CREDENTIALS
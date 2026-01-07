# VTS Backup System - Complete Setup Guide

## ✅ Production-Ready Service Account Setup for Render

This guide covers **Service Account authentication** for automated backups on Render (no browser required).

---

## 📋 Step-by-Step Setup

### Step 1: Create Service Account in Google Cloud Console

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Make sure project **vts-backup-tool** is selected (top dropdown)

2. **Enable Google Drive API**
   - Navigate to: **APIs & Services** → **Library**
   - Search for: **Google Drive API**
   - Click **ENABLE**

3. **Create Service Account**
   - Navigate to: **IAM & Admin** → **Service Accounts**
   - Click **+ CREATE SERVICE ACCOUNT**
   - Fill in:
     - **Service account name:** `vts-backup-service`
     - **Service account ID:** auto-fills (leave as-is)
     - **Description:** `VTS automated backup to Google Drive`
   - Click **CREATE AND CONTINUE**

4. **Grant Permissions**
   - On "Grant this service account access to project" screen:
     - Click **Select a role** dropdown
     - Search for and select **Editor** (or **Drive API Editor** if available)
   - Click **CONTINUE**
   - Click **DONE**

5. **Create and Download JSON Key**
   - Back on the Service Accounts page, click on **vts-backup-service** (the one you just created)
   - Go to the **KEYS** tab
   - Click **ADD KEY** → **Create new key**
   - Select **JSON** format
   - Click **CREATE**
   - A JSON file auto-downloads (usually named `vts-backup-tool-xxx.json`)
   - **Save this file securely** — this is your service account key!

---

### Step 2: Share Google Drive Folder with Service Account

1. **Open Google Drive**
   - Go to: https://drive.google.com/

2. **Find or Create VTS_Backups Folder**
   - Look for folder named **VTS_Backups**
   - If it doesn't exist, create it (right-click → New folder → name it **VTS_Backups**)

3. **Share with Service Account**
   - Right-click on **VTS_Backups** folder → **Share**
   - In the JSON key file you downloaded, find the `"client_email"` field
     - It looks like: `vts-backup-service@vts-backup-tool.iam.gserviceaccount.com`
   - **Paste that email** in the Share dialog
   - Give it **Editor** access
   - Click **Share**
   - ✅ **IMPORTANT:** Uncheck "Notify people" (since it's a service account)

---

### Step 3: Add Credentials to Render Environment

You have two options for adding credentials to Render:

#### Option A: Using Secret Files (Recommended - You're using this! ✅)

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com/
   - Click on your **VTS service**

2. **Add Secret File**
   - Click **Environment** (left sidebar)
   - Scroll down to **Secret Files** section
   - Click **Add Secret File**
   - Set:
     - **Filename:** `/etc/secrets/google_service_account.json`
     - **Contents:** Paste the entire JSON content from your downloaded service account key file
   - Click **Save**

3. **Add Environment Variable**
   - In the **Environment Variables** section (above Secret Files)
   - Click **Add Environment Variable**
   - Set:
     - **Key:** `GOOGLE_APPLICATION_CREDENTIALS`
     - **Value:** `/etc/secrets/google_service_account.json`
   - Click **Add**
   - Click **Save Changes**

   ✅ **You already have this configured!**

#### Option B: Using Environment Variable (Alternative)

1. **Open the JSON Key File**
   - Open the downloaded JSON file in VS Code or any text editor

2. **Copy the Entire JSON Content**
   - Select all text from the opening `{` to the closing `}`

3. **Go to Render Dashboard**
   - Click **Environment** (left sidebar)
   - Click **Add Environment Variable**
   - Set:
     - **Key:** `GOOGLE_CREDENTIALS_JSON`
     - **Value:** Paste the entire JSON content
   - Click **Save Changes**

---

### Step 4: Configure SMTP for Email Notifications

**For Gmail:**

1. **Enable 2-Factor Authentication**
   - Go to: https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Generate App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select: **App** → Mail, **Device** → Other (Custom name)
   - Name it: `VTS Backup`
   - Click **Generate**
   - Copy the 16-character password

3. **Add to Render Environment**
   - In Render Dashboard → Environment → Add Environment Variable:
     - **Key:** `SMTP_SERVER` → **Value:** `smtp.gmail.com`
     - **Key:** `SMTP_PORT` → **Value:** `587`
     - **Key:** `SMTP_USERNAME` → **Value:** `your-email@gmail.com`
     - **Key:** `SMTP_PASSWORD` → **Value:** (paste the app password from step 2)
   - Click **Save Changes**

---

### Step 5: Deploy and Test

1. **Trigger Deployment**
   - Click **Manual Deploy** on your Render service
   - OR push a commit to trigger auto-deploy

2. **Wait for Deployment**
   - Wait for deployment to complete (check logs)

3. **Test Backup**
   - Navigate to your VTS app
   - Go to **Backup Management** page (Resident Engineer access)
   - Click **☁️ Run Full Backup to Google Drive**
   - Monitor the logs for success messages

4. **Verify in Google Drive**
   - Check your Google Drive **VTS_Backups** folder
   - You should see:
     - `vts_database_backup_YYYYMMDD_HHMMSS.db`
     - `uploaded_images_backup_YYYYMMDD_HHMMSS.zip`

5. **Check Email**
   - You should receive an email notification at `hebtron25@gmail.com`

---

## 🔄 Backup Schedule

- **Automatic backups:** Every 21 hours (configured in `backup_scheduler.py`)
- **Manual backups:** Available in Backup Management page
  - **Local backup only:** Stores files locally without Google Drive upload
  - **Full backup to Google Drive:** Uploads to Drive and sends email notifications
  - **Rate limit:** Full Google Drive backup can only run once every 3 hours

---

## 🐛 Troubleshooting

### Issue: "Service Account authentication failed"

**Solution:**
- Verify `GOOGLE_CREDENTIALS_JSON` is set correctly in Render
- Ensure JSON is valid (copy entire content, no truncation)
- Check that service account has Drive API access

### Issue: "Access denied" or "Permission denied"

**Solution:**
- Verify you shared the `VTS_Backups` folder with the service account email
- Check that Editor permissions were granted
- Wait a few minutes for permissions to propagate

### Issue: "Email notification failed"

**Solution:**
- Verify SMTP credentials are correct
- If using Gmail, ensure you're using an App Password (not regular password)
- Check that 2FA is enabled on your Google account

### Issue: "Database file not found"

**Solution:**
- This is normal if using PostgreSQL on Render (not SQLite)
- The app backs up PostgreSQL differently
- Check logs to ensure PostgreSQL dump is working

---

## 📁 File Structure

```
d:\gps-report-tool\
├── backup_script.py          # Main backup script (Service Account ready)
├── backup_scheduler.py       # Scheduler for automatic backups
├── backup_management.py      # Streamlit UI for backup management
├── secrets_utils.py          # Credential management utilities
├── backups/                  # Local backup storage
│   ├── vts_database_backup_*.db
│   └── uploaded_images_backup_*.zip
├── uploaded_accident_images/ # Images to backup
└── vts_database.db          # SQLite database (local only)
```

---

## 🔐 Security Best Practices

✅ **DO:**
- Use Service Account for production (Render, AWS, etc.)
- Store credentials in environment variables
- Use Secrets Manager (AWS/Azure) for sensitive data
- Enable 2FA and use App Passwords for SMTP

❌ **DON'T:**
- Commit `credentials.json` or service account keys to Git
- Share service account keys publicly
- Use regular Gmail passwords (always use App Passwords)
- Store credentials in code

---

## 📖 Additional Resources

- **Google Cloud Console:** https://console.cloud.google.com/
- **Google Drive API Docs:** https://developers.google.com/drive/api
- **Gmail App Passwords:** https://myaccount.google.com/apppasswords
- **Render Documentation:** https://render.com/docs

---

## 🆘 Support

For issues or questions:
1. Check the logs: `backup.log` and `backup_scheduler.log`
2. Review error messages in Streamlit UI
3. Verify environment variables in Render Dashboard
4. Ensure Google Drive folder permissions are correct

---

## ✅ Verification Checklist

Before going live, verify:

- [ ] Service Account created in Google Cloud Console
- [ ] Google Drive API enabled
- [ ] Service account JSON key downloaded
- [ ] VTS_Backups folder created in Google Drive
- [ ] VTS_Backups folder shared with service account email (Editor access)
- [ ] `GOOGLE_CREDENTIALS_JSON` environment variable set in Render
- [ ] SMTP credentials configured in Render
- [ ] Gmail App Password generated (if using Gmail)
- [ ] Test backup successful
- [ ] Backup files visible in Google Drive
- [ ] Email notification received

---

**Last Updated:** 2026-01-07  
**Version:** 2.0 (Service Account Ready)
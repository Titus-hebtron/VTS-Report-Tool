# Google Drive Authentication Setup for VTS Backup Tool

## Project Information
- **Project Name:** VTS Backup Tool
- **Project ID:** vts-backup-tool
- **Project Number:** 657781609471

---

## Step 1: Create OAuth 2.0 Credentials in Google Cloud Console

### 1.1 Go to Google Cloud Console
- Visit: https://console.cloud.google.com/
- Select your project **vts-backup-tool** (or create it if needed)

### 1.2 Enable Google Drive API
- In the left sidebar, click **APIs & Services** > **Library**
- Search for **Google Drive API**
- Click on it and press **ENABLE**

### 1.3 Create OAuth 2.0 Credentials
- Click **APIs & Services** > **Credentials** (left sidebar)
- Click **+ CREATE CREDENTIALS** > **OAuth client ID**
- If prompted to create a consent screen, click **CONFIGURE CONSENT SCREEN**
  - Select **User Type**: External
  - Fill in App name: `VTS Backup Tool`
  - Add your email as Support email
  - Click **SAVE AND CONTINUE**
  - On "Scopes" page, click **SAVE AND CONTINUE**
  - On "Test users" page, add your email and click **SAVE AND CONTINUE**
  - Review and click **BACK TO DASHBOARD**

### 1.4 Download Credentials JSON
- Go back to **Credentials** > **+ CREATE CREDENTIALS** > **OAuth client ID**
- Select **Desktop application** as Application type
- Click **CREATE**
- Click the download icon (⬇️) to download the JSON file
- Save it as `credentials.json` in your project root directory

---

## Step 2: Download and Place credentials.json

1. Place the downloaded `credentials.json` file in your project root directory:
   ```
   d:\gps-report-tool\credentials.json
   ```

2. Make sure the file contains:
   - `client_id`
   - `client_secret`
   - `auth_uri`
   - `token_uri`
   - Other OAuth fields

---

## Step 3: First-Time Authentication

When you run the backup application for the first time:

1. Navigate to the **Backup Management** page in your Streamlit app
2. Click **☁️ Run Full Backup to Google Drive**
3. A browser window will open asking you to authenticate with your Google account
4. Grant the permissions when prompted (this allows VTS to access your Google Drive)
5. A `token.pickle` file will be created automatically
6. Future backups will use this token without needing re-authentication

---

## Step 4: Verify Setup

After successful authentication:
- ✅ `token.pickle` file should exist in your project root
- ✅ Google Drive backups should work
- ✅ Check your Google Drive for a **VTS Backup Tool** folder containing backups

---

## Troubleshooting

### Issue: "credentials.json not found"
**Solution:** Make sure you've downloaded and saved the credentials.json file in the project root directory

### Issue: "Authorization required" or "Invalid credentials"
**Solution:** Delete `token.pickle` and restart the app to re-authenticate

### Issue: "Google API client not installed"
**Solution:** Run this command:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Issue: "Access to the Google Drive API has not been granted"
**Solution:** 
- Go to https://console.cloud.google.com/
- Verify the Google Drive API is **ENABLED**
- Verify OAuth consent screen is configured
- Delete `token.pickle` and re-authenticate

### Issue: "Quota exceeded" or "Too many requests"
**Solution:** This is a rate limit. Wait a few minutes before trying again.

---

## Manual Backup Options

If Google Drive authentication is not configured:

### Option 1: Local Backup Only
- Click **🚀 Run Local Backup Only** button
- Backups are stored in the `backups/` directory
- You can download them manually from the **Download Backups** tab

### Option 2: Configure Later
- Set up Google Drive credentials when ready
- All previously created local backups will still be available

---

## Automation (Scheduled Backups)

For automated daily backups to Google Drive, use the **Backup Settings** tab to configure the scheduler.

---

## Security Notes

⚠️ **Important:**
- Never commit `credentials.json` or `token.pickle` to Git
- These files contain sensitive authentication information
- Add them to `.gitignore`:
  ```
  credentials.json
  token.pickle
  ```

---

## Support

For more information:
- Google Cloud Console: https://console.cloud.google.com/
- Google Drive API Docs: https://developers.google.com/drive/api

# Render Deployment Guide

## Issue Fixed: DATABASE_URL Validation Error

### Problem
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string
```

This error occurred on Render when `DATABASE_URL` environment variable was:
- Set but empty
- Malformed or missing protocol prefix
- Not a valid PostgreSQL connection string

### Solution Applied

✅ **Fixed `db_utils.py`** with proper validation:
- Checks if `DATABASE_URL` is not empty
- Validates it starts with `postgresql://` or `postgres://`
- Provides debug logging for troubleshooting
- Automatically falls back to SQLite if invalid

✅ **Created `validate_env.py`** to test environment:
- Validates DATABASE_URL format
- Tests actual database connection
- Provides clear error messages

---

## How to Deploy on Render

### Step 1: Set Environment Variables

In your Render dashboard, go to your web service and add:

```bash
DATABASE_URL=postgresql://username:password@host:5432/database
```

**Get this from your PostgreSQL service:**
1. Go to your PostgreSQL database in Render dashboard
2. Click on "Connect" or "Info"
3. Copy the "External Database URL"
4. Paste it as `DATABASE_URL` in your web service environment variables

### Step 2: Validate Configuration (Optional)

SSH into your Render service and run:

```bash
python validate_env.py
```

This will check if `DATABASE_URL` is properly configured.

### Step 3: Deploy

Push your changes to trigger a deployment:

```bash
git push origin master
```

Render will automatically rebuild and deploy.

---

## Common Issues & Solutions

### Issue 1: Empty DATABASE_URL

**Symptom:**
```
⚠️  DATABASE_URL is set but empty - using SQLite
```

**Solution:**
- Check Render dashboard environment variables
- Ensure DATABASE_URL has a value (not just the key)
- Copy the connection string from your PostgreSQL service

### Issue 2: Wrong Format

**Symptom:**
```
⚠️  DATABASE_URL doesn't start with postgresql:// or postgres://
```

**Solution:**
- Ensure URL starts with `postgresql://` or `postgres://`
- Format: `postgresql://user:password@host:5432/database`
- Don't use other protocols like `postgres+psycopg2://`

### Issue 3: Database Connection Timeout

**Symptom:**
```
⚠️  PostgreSQL failed: timeout expired
🔄 Using SQLite instead
```

**Solution:**
- Free tier databases sleep after 15 minutes
- First connection takes 30-60 seconds
- App will automatically retry and fall back to SQLite if needed
- Consider upgrading to paid tier ($7/month) for always-on database

### Issue 4: SSL Connection Closed

**Symptom:**
```
⚠️  PostgreSQL failed: SSL connection has been closed unexpectedly
```

**Solution:**
- Already fixed in code (using `sslmode: prefer`)
- Database might be waking up from sleep
- App will automatically fall back to SQLite

---

## Automatic Fallback Behavior

The app is now configured with intelligent fallback:

1. **Tries PostgreSQL first** (if DATABASE_URL is valid)
2. **Waits up to 30 seconds** for connection
3. **Falls back to SQLite** if PostgreSQL fails
4. **Logs clear messages** about what's happening

This means:
- ✅ App always works (never crashes on startup)
- ✅ Uses PostgreSQL in production when available
- ✅ Uses SQLite as backup (data persistence may be limited)

---

## Verifying Deployment

After deployment, check Render logs for:

```
ℹ️  DATABASE_URL detected: dpg-xxx.singapore-postgres.render.com
✅ PostgreSQL connected
Checking database initialization...
✅ Database initialization completed successfully
```

Or if it falls back:

```
⚠️  PostgreSQL failed: [error message]
🔄 Using SQLite instead
✅ Using SQLite database: vts_database.db
```

---

## Production Best Practices

### For Paid Tier Database
- ✅ Always-on (no sleep)
- ✅ Faster connections
- ✅ Better reliability
- ✅ Recommended for production

### For Free Tier Database
- ⚠️  Sleeps after 15 minutes
- ⚠️  First connection slow (30-60s)
- ⚠️  May time out occasionally
- ✅ Good for testing/staging

### SQLite Fallback
- ✅ Instant startup
- ✅ No external dependencies
- ⚠️  Data may not persist across deploys
- ⚠️  Not recommended for production
- ✅ Perfect for local development

---

## Testing Locally Before Deploy

```bash
# Test with your Render DATABASE_URL
export DATABASE_URL="postgresql://..."  # or set in .env
python validate_env.py

# Run the app
streamlit run auth.py
# or
uvicorn api:app --reload
```

---

## Need Help?

Check these resources:
- `DATABASE_FIX_SUMMARY.md` - Complete fix documentation
- `DATABASE_TROUBLESHOOTING.md` - Troubleshooting guide  
- Render logs - Check for error messages
- Render support - Contact if database won't connect
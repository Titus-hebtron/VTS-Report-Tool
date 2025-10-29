#!/usr/bin/env python3
"""
Backup Scheduler Service
Runs as a Windows service or background process to trigger backups every 21 hours
"""

import os
import time
import datetime
import subprocess
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    filename='backup_scheduler.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_backup():
    """Execute the backup script"""
    try:
        logging.info("Starting scheduled backup...")

        # Run the backup script
        result = subprocess.run([
            sys.executable, 'backup_script.py'
        ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout

        if result.returncode == 0:
            logging.info("Backup completed successfully")
            logging.info(f"Backup output: {result.stdout}")
        else:
            logging.error(f"Backup failed with return code {result.returncode}")
            logging.error(f"Backup stderr: {result.stderr}")
            logging.error(f"Backup stdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        logging.error("Backup timed out after 1 hour")
    except Exception as e:
        logging.error(f"Failed to run backup: {e}")

def calculate_next_backup_time():
    """Calculate when the next backup should run (every 21 hours)"""
    now = datetime.datetime.now()
    # Next backup at the same time tomorrow + 3 hours (21 hours total)
    next_backup = now + datetime.timedelta(hours=21)
    return next_backup

def main():
    """Main scheduler loop"""
    logging.info("Backup scheduler started")

    while True:
        try:
            # Calculate next backup time
            next_backup = calculate_next_backup_time()
            wait_seconds = (next_backup - datetime.datetime.now()).total_seconds()

            if wait_seconds > 0:
                logging.info(f"Next backup scheduled for: {next_backup}")
                time.sleep(min(wait_seconds, 3600))  # Sleep for up to 1 hour, then check again
            else:
                # Time to run backup
                run_backup()

                # Brief pause before calculating next backup
                time.sleep(60)

        except KeyboardInterrupt:
            logging.info("Backup scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
            time.sleep(300)  # Wait 5 minutes on error

if __name__ == "__main__":
    main()
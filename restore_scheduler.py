#!/usr/bin/env python3
"""
Restore Scheduler
Schedules automatic database restoration every day at 06:00
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
    filename='restore_scheduler.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_restore():
    """Execute the restore script"""
    try:
        logging.info("Starting scheduled database restore...")

        # Run the restore script
        result = subprocess.run([
            sys.executable, 'restore_script.py'
        ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout

        if result.returncode == 0:
            logging.info("Restore completed successfully")
            logging.info(f"Restore output: {result.stdout}")
        else:
            logging.error(f"Restore failed with return code {result.returncode}")
            logging.error(f"Restore stderr: {result.stderr}")
            logging.error(f"Restore stdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        logging.error("Restore timed out after 30 minutes")
    except Exception as e:
        logging.error(f"Failed to run restore: {e}")

def calculate_next_restore_time():
    """Calculate when the next restore should run (every day at 06:00)"""
    now = datetime.datetime.now()

    # Next restore at 06:00 tomorrow
    next_restore = now.replace(hour=6, minute=0, second=0, microsecond=0)

    # If it's already past 06:00 today, schedule for tomorrow
    if now >= next_restore:
        next_restore = next_restore + datetime.timedelta(days=1)

    return next_restore

def main():
    """Main scheduler loop"""
    logging.info("Restore scheduler started")

    while True:
        try:
            # Calculate next restore time
            next_restore = calculate_next_restore_time()
            wait_seconds = (next_restore - datetime.datetime.now()).total_seconds()

            if wait_seconds > 0:
                logging.info(f"Next restore scheduled for: {next_restore}")
                time.sleep(min(wait_seconds, 3600))  # Sleep for up to 1 hour, then check again
            else:
                # Time to run restore
                run_restore()

                # Brief pause before calculating next restore
                time.sleep(60)

        except KeyboardInterrupt:
            logging.info("Restore scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
            time.sleep(300)  # Wait 5 minutes on error

if __name__ == "__main__":
    main()
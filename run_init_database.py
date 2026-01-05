import traceback
import sys
from db_utils import init_database, _mask_db_url, DATABASE_URL

print('DATABASE_URL (masked):', _mask_db_url(DATABASE_URL))

try:
    init_database()
    print('init_database() completed successfully')
except Exception:
    traceback.print_exc()
    sys.exit(1)

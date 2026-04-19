from typing import Final

# Offline-First Rules
MAX_OFFLINE_DAYS: Final[int] = 30
GRACE_PERIOD_DAYS: Final[int] = 7
SYNC_VERSION_INCREMENT: Final[int] = 1

# Header Keys for Desktop App
HEADER_MACHINE_ID: Final[str] = 'X-Machine-Id'
HEADER_LICENSE_KEY: Final[str] = 'X-License-Key'

# Plan Range Keys
LIMIT_USERS: Final[str] = 'max_users'
LIMIT_MACHINES: Final[str] = 'max_machines'
LIMIT_INVOICES: Final[str] = 'max_monthly_invoices'

# Metadata Keys
META_LAST_SYNC: Final[str] = 'last_sync_at'
META_HW_INFO: Final[str] = 'hardware_snapshot'

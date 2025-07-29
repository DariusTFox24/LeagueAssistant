# Test script to check coordinator update timing
# Run this in Home Assistant logs to see update frequency

import logging
import asyncio
from datetime import datetime

# Enable debug logging for the integration
logging.getLogger('custom_components.riot_lol').setLevel(logging.DEBUG)

def log_update_times():
    """Log current time to track update frequency."""
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] Coordinator should update around this time")

# Schedule logging every minute to compare with actual updates
print("=== COORDINATOR UPDATE TRACKER ===")
print("Watch Home Assistant logs for 'Starting data update cycle...' messages")
print("They should appear every 60 seconds")
print("")
print("Current time:", datetime.now().strftime("%H:%M:%S"))
print("Next expected update times:")
for i in range(1, 6):
    future_time = datetime.now().timestamp() + (i * 60)
    future_dt = datetime.fromtimestamp(future_time)
    print(f"  {future_dt.strftime('%H:%M:%S')}")

print("")
print("Check Home Assistant logs for:")
print("  - 'Starting data update cycle...' (should appear every 60 seconds)")
print("  - 'Successfully fetched summoner level: X' (level should not be 0)")
print("  - Any error messages")

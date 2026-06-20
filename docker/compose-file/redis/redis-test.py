#!/usr/bin/env python3
"""
Redis Sentinel Failover Monitor
--------------------------------
Configuration is set directly in this file.
Checks that the key "dev" with value "ops" exists on the current Redis master
(discovered via Sentinels). Alerts on missing key, wrong value, or connection loss.
"""

import time
import redis
from redis.exceptions import ConnectionError, TimeoutError, ResponseError

# ===================================================================
#  CONFIGURATION – change these to match your environment
# ===================================================================

# List of Sentinel IP:port pairs
SENTINEL_HOSTS = [
    ("192.168.59.20", 26380),
    ("192.168.59.21", 26380),
    ("192.168.59.24", 26380),
]

# Name of the monitored master (from sentinel.conf)
MASTER_NAME = "mymaster"

# Key & value to monitor
CHECK_KEY = "dev"
EXPECTED_VALUE = "ops"

# Check interval (seconds)
CHECK_INTERVAL = 2

# Connection timeout (seconds)
SOCKET_TIMEOUT = 3

# -------------------------------------------------------------------
# Credentials for connecting to the SENTINEL processes
# (must exist in your Sentinel ACL if ACL is enabled)
# -------------------------------------------------------------------
SENTINEL_USER = "sentinel"           # or "default" if no ACL
SENTINEL_PASS = "f76ebff2d7c30c43810cd481"

# -------------------------------------------------------------------
# Credentials for connecting to the REDIS DATA NODES (master/replicas)
# (must exist in users.acl)
# -------------------------------------------------------------------
REDIS_USER = "develop"              # user that can SET/GET the key
REDIS_PASS = "c8133e1a55aef5264c4e"

# ===================================================================
#  END OF CONFIGURATION
# ===================================================================

def test_sentinel(host, port):
    """Test a single Sentinel and return (True, master_address) if successful."""
    print(f"\nTesting Sentinel {host}:{port} ...")
    try:
        client = redis.Redis(
            host=host, port=port,
            username=SENTINEL_USER, password=SENTINEL_PASS,
            socket_timeout=SOCKET_TIMEOUT,
            decode_responses=True
        )
        # 1. Authenticate + ping
        pong = client.ping()
        print(f"  ✅ PING: {pong}")

        # 2. Get master address
        addr = client.sentinel_get_master_addr_by_name(MASTER_NAME)
        if addr:
            print(f"  ✅ Master address: {addr}")
            return True, addr
        else:
            print(f"  ⚠ Master '{MASTER_NAME}' not known to this sentinel")
            return False, None

    except ResponseError as e:
        print(f"  ❌ AUTH ERROR: {e}")
        return False, None
    except (ConnectionError, TimeoutError) as e:
        print(f"  ❌ CONNECTION ERROR: {e}")
        return False, None
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False, None

def discover_master_via_sentinels():
    """Query all sentinels and return the first valid master address."""
    print("Discovering master via Sentinels...")
    for host, port in SENTINEL_HOSTS:
        ok, addr = test_sentinel(host, port)
        if ok and addr:
            return addr
    return None

def monitor_master(host, port):
    """Monitor the key on the given master address."""
    print(f"\nStarting key monitor on master {host}:{port} ...")
    while True:
        try:
            client = redis.Redis(
                host=host, port=port,
                username=REDIS_USER, password=REDIS_PASS,
                socket_timeout=SOCKET_TIMEOUT,
                decode_responses=True
            )
            # Create key only if it does not exist
            client.set(CHECK_KEY, EXPECTED_VALUE, nx=True)
            value = client.get(CHECK_KEY)

            if value is None:
                print(f"� ALERT: Key '{CHECK_KEY}' DOES NOT EXIST!")
            elif value != EXPECTED_VALUE:
                print(f"� ALERT: Key '{CHECK_KEY}' = '{value}' (expected '{EXPECTED_VALUE}')")
            else:
                print(f"✅ OK: {CHECK_KEY} = {value}")

            time.sleep(CHECK_INTERVAL)

        except (ConnectionError, TimeoutError) as e:
            print(f"� CONNECTION LOST to {host}:{port} - {e}")
            print("   Trying to re-discover new master...")
            return False   # trigger re-discovery
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(CHECK_INTERVAL)

def main():
    print("=" * 60)
    print("Redis Sentinel Failover Monitor")
    print("=" * 60)

    while True:
        master_addr = discover_master_via_sentinels()
        if master_addr is None:
            print("\n❌ No master found from any Sentinel. Retrying in 5s...")
            time.sleep(5)
            continue

        ok = monitor_master(master_addr[0], master_addr[1])
        if not ok:
            continue   # re-discover

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✓ Stopped by user.")
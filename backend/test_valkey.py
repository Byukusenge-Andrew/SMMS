import os
import redis
from decouple import config
import socket

def test_redis():
    try:
        host = config('REDIS_HOST')
        port = config('REDIS_PORT', cast=int)
        password = config('REDIS_PASSWORD')
        username = config('REDIS_USERNAME', default='default')
        
        print(f"--- Valkey/Redis Diagnostics ---")
        print(f"Attempting to resolve hostname: {host}")
        
        try:
            ip = socket.gethostbyname(host)
            print(f"✅ Hostname resolved to: {ip}")
        except socket.gaierror:
            print(f"❌ Hostname resolution (DNS) failed.")
            if '.i.aivencloud.com' in host:
                alt_host = host.replace('.i.aivencloud.com', '.aivencloud.com')
                print(f"💡 Suggestion: If 'i.aivencloud.com' is internal-only, try '{alt_host}'")
            print(f"⚠️  Note: If the Aiven dashboard says 'Rebuilding', the DNS records may not be live yet. Wait for 'Running'.")
            return

        print(f"Testing connection to {host}:{port}...")
        
        # Use SSL for Aiven (rediss://)
        r = redis.Redis(
            host=host,
            port=port,
            password=password,
            username=username,
            ssl=True,
            ssl_cert_reqs=None,
            socket_timeout=5
        )
        
        ping = r.ping()
        if ping:
            print("✅ Successfully connected to Valkey!")
            r.set('keativ_test_ping', 'ok')
            val = r.get('keativ_test_ping')
            print(f"✅ Data persistence test: {val.decode('utf-8')}")
        else:
            print("❌ Connection successful but ping failed.")
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == "__main__":
    test_redis()


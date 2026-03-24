import socket
import requests
import time

def check_connectivity():
    targets = [
        ("google.com", 443),
        ("api.twitter.com", 443),
        ("api.github.com", 443),
    ]
    
    print("--- Network Diagnostics ---")
    
    for host, port in targets:
        print(f"\nChecking {host}:{port}...")
        
        # DNS Resolution
        try:
            ip = socket.gethostbyname(host)
            print(f"✅ DNS: {host} -> {ip}")
        except socket.gaierror as e:
            print(f"❌ DNS: Failed to resolve {host}: {e}")
            continue
            
        # Socket Connection
        start = time.time()
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                duration = (time.time() - start) * 1000
                print(f"✅ Socket: Connected in {duration:.2f}ms")
        except Exception as e:
            print(f"❌ Socket: Connection failed: {e}")
            continue
            
        # HTTP Request
        try:
            url = f"https://{host}"
            resp = requests.get(url, timeout=5)
            print(f"✅ HTTP: {host} returned {resp.status_code}")
        except Exception as e:
            print(f"❌ HTTP: Request failed: {e}")

if __name__ == "__main__":
    check_connectivity()

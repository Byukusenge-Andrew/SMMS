#!/usr/bin/env python
"""
Debug the Supabase service role key
"""

import base64
import json

# The service role key from your .env
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1ZGV1aWV2d25wdm11eWVibWdjIiwicm9zZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDExNjk3MywiZXhwIjoyMDY5NjkyOTczfQ.nsymKougaTsVPpQzFCTGNcYEeoYnbAWnId-pk_P7hNs"

def decode_jwt_payload(token):
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        # Base64 URL decode the payload (second part)
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        data = base64.urlsafe_b64decode(padded.encode("utf-8"))
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

payload = decode_jwt_payload(service_key)
print("🔍 JWT Payload Analysis:")
print(json.dumps(payload, indent=2))

# Check for issues
issues = []

if payload.get("iss") != "supabase":
    issues.append("❌ Invalid issuer")

if payload.get("ref") != "cudeuievwnpvmuyebmgc":
    issues.append("❌ Invalid project reference")

# Check for the typo!
if "rose" in payload:
    issues.append("❌ TYPO FOUND: 'rose' should be 'role'")

if payload.get("role") != "service_role":
    issues.append("❌ Invalid role - expected 'service_role'")

# Check expiration
import time
current_time = int(time.time())
exp = payload.get("exp", 0)
if exp < current_time:
    issues.append("❌ Token has expired")

if issues:
    print("\n🚨 Issues found:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("\n✅ JWT looks valid!")
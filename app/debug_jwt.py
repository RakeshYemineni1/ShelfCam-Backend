from jose import jwt
import json
from datetime import datetime

def decode_jwt_token(token, secret_key="your_super_secret_key"):
    """Decode JWT token without verification (for debugging)"""
    try:
        # Decode without verification to see contents
        decoded_payload = jwt.decode(token, key="", options={"verify_signature": False})

        print("🔍 JWT Token Contents:")
        print(json.dumps(decoded_payload, indent=2, default=str))
        
        # Check expiration
        if 'exp' in decoded_payload:
            exp_time = datetime.fromtimestamp(decoded_payload['exp'])
            now = datetime.now()
            print(f"\n⏰ Token expires at: {exp_time}")
            print(f"⏰ Current time: {now}")
            print(f"⏰ Token valid: {'✅ Yes' if exp_time > now else '❌ Expired'}")
        
        return decoded_payload
        
    except Exception as e:
        print(f"❌ Error decoding token: {e}")
        return None

# Test with your token
if __name__ == "__main__":
    # Replace with your actual JWT token
    your_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYW5hZ2VyMSIsInJvbGUiOiJzdG9yZV9tYW5hZ2VyIiwiZW1wbG95ZWVfaWQiOiJFMjAxIiwiZXhwIjoxNzUxNzgzMzY5fQ.VZzHDVKhVfrV8a_UC95biDUdGk02pgyraV3QMpKrP_s"
    
    print("🔓 JWT Token Debugger")
    print("=" * 50)
    
    # Paste your token here
    token_input = input("📋 Paste your JWT token here: ").strip()
    
    if token_input:
        decode_jwt_token(token_input)
    else:
        print("❌ No token provided")

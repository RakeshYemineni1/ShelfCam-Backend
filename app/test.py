import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import verify_password

plain = "staffpass"
hashed = "$2b$12$e3Qs1V6FBxS7ZmMJv37cEOGX3liCJpsgDq0PH5ecfwVGQh8scyRAy"

print(verify_password(plain, hashed))

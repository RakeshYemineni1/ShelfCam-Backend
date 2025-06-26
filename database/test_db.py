import psycopg2

try:
    conn = psycopg2.connect("postgres://postgres:Ajantha123@localhost:5432/shelfCam_auth")
    print("✅ Connected successfully!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)

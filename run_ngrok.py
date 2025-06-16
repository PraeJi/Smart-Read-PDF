from pyngrok import ngrok, conf
import os

# ✅ ใช้ NGROK_AUTHTOKEN จาก env
conf.get_default().auth_token = os.getenv("NGROK_AUTHTOKEN")

from smart_upload import app

# ✅ เปิด tunnel ไปยัง port 5000
public_url = ngrok.connect(5000)
print("🚀 Ngrok tunnel URL:", public_url)

# ✅ รัน Flask app บน host ทุก IP ใน container
app.run(host="0.0.0.0", port=5000)

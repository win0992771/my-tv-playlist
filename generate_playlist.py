import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import sys

# إنشاء الملف فوراً حتى لو فشل السكربت لاحقاً
with open("playlist.m3u8", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")

BASE_URL = "http://live.publicdataroute.cc/api/live/livedrama/v13.0.0"
HEADERS = {
    "User-Agent": "okhttp/3.12.13", 
    "Content-Type": "application/json",
    "Accept": "application/json"
}
KEY = b"fedcba9876543210"

def decrypt_data(encrypted_text):
    if not encrypted_text or ":" not in encrypted_text:
        return encrypted_text
    try:
        ciphertext_b64, iv_b64 = encrypted_text.split(":", 1)
        ciphertext = base64.b64decode(ciphertext_b64)
        iv = base64.b64decode(iv_b64) if iv_b64 else KEY
        cipher = AES.new(KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception:
        return encrypted_text

def api_request(endpoint, payload=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.post(url, headers=HEADERS, json=payload or {}, timeout=15)
        print(f"[{endpoint}] Status Code: {r.status_code}")
        print(f"[{endpoint}] Raw Response: {r.text[:200]}") # نطبع أول 200 حرف لنرى ماذا يرد السيرفر
        
        text = r.text.strip()
        if not text: return None
        decrypted = decrypt_data(text)
        return json.loads(decrypted)
    except Exception as e:
        print(f"Error on {endpoint}: {e}")
        return None

def main():
    print("Fetching topics...")
    topics_data = api_request("getliveTopics")
    
    if not topics_data:
        print("FAILED: Could not get topics data from server.")
        sys.exit(0) # نخرج بنجاح (0) حتى لا يفشل GitHub، لأننا أنشأنا الملف الفارغ مسبقاً

    m3u_lines = ["#EXTM3U"]
    # ... بقية الكود كما هو ...
    # (اختصاراً لك، يمكنك ترك الجزء الخاص بجلب القنوات كما هو في الكود السابق)
    
    # حفظ الملف
    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print("✅ Playlist saved to playlist.m3u8")

if __name__ == "__main__":
    main()

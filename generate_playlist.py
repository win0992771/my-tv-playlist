
import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ==========================================
# إعدادات الاتصال بالسيرفر (API)
# ==========================================
BASE_URL = "http://live.publicdataroute.cc/api/live/livedrama/v13.0.0"
# الهيدرز: قد تحتاج لتعديلها إذا رفض السيرفر الطلبات
HEADERS = {
    "User-Agent": "okhttp/3.12.13", 
    "Content-Type": "application/json",
    "Accept": "application/json"
}
# مفتاح فك التشفير الذي استخرجناه سابقاً (fedcba9876543210)
KEY = b"fedcba9876543210"

# ==========================================
# دالة فك تشفير AES
# ==========================================
def decrypt_data(encrypted_text):
    if not encrypted_text or ":" not in encrypted_text:
        return encrypted_text
    try:
        # الرد المشفر يكون بصيغة: Base64(Ciphertext):Base64(IV)
        ciphertext_b64, iv_b64 = encrypted_text.split(":", 1)
        ciphertext = base64.b64decode(ciphertext_b64)
        iv = base64.b64decode(iv_b64) if iv_b64 else KEY
        
        cipher = AES.new(KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        # إذا فشل الفك، نعيد النص الأصلي (قد يكون غير مشفر)
        return encrypted_text

# ==========================================
# دالة إرسال الطلبات إلى API
# ==========================================
def api_request(endpoint, payload=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.post(url, headers=HEADERS, json=payload or {}, timeout=15)
        if r.status_code != 200:
            return None
        
        text = r.text.strip()
        if not text:
            return None
            
        # فك التشفير إذا لزم الأمر
        decrypted = decrypt_data(text)
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return None
    except Exception as e:
        print(f"Request error for {endpoint}: {e}")
        return None

# ==========================================
# الدالة الرئيسية لجلب الروابط وبناء M3U8
# ==========================================
def main():
    m3u_lines = ["#EXTM3U"]
    
    print("Fetching topics...")
    topics_data = api_request("getliveTopics")
    if not topics_data or "live_topics" not in topics_data:
        print("Failed to get topics.")
        return

    for topic in topics_data["live_topics"]:
        topic_id = topic.get("id_topic")
        topic_name = topic.get("name_topic", "Unknown")
        if not topic_id:
            continue
        
        print(f"Fetching channels for: {topic_name}")
        channels_data = api_request("getLiveByTopic", {"id_topic": topic_id})
        if not channels_data or "live" not in channels_data:
            continue

        for ch in channels_data["live"]:
            ch_id = ch.get("id_live")
            ch_name = ch.get("name", "Unknown")
            ch_logo = ch.get("img_url", "")
            if not ch_id:
                continue

            # جلب رابط البث للقناة
            stream_data = api_request("getLiveAllStreamsById", {"id_live": ch_id})
            if not stream_data:
                continue

            final_url = None
            headers = {}

            # استخراج الرابط من الرد (قد يكون متداخلاً ومشفراً)
            if "data" in stream_data and "url" in stream_data["data"]:
                raw_url = stream_data["data"]["url"]
                decrypted_raw = decrypt_data(raw_url)
                
                try:
                    inner_json = json.loads(decrypted_raw)
                    if "url" in inner_json:
                        final_url = inner_json["url"]
                        headers = inner_json.get("headers", {})
                except:
                    # إذا لم يكن JSON، فقد يكون الرابط مباشراً
                    final_url = decrypted_raw

            if final_url:
                # إضافة الهيدرز كـ EXTVLCOPT لتشغيلها في VLC
                logo_attr = f' tvg-logo="{ch_logo}"' if ch_logo else ""
                m3u_lines.append(f'#EXTINF:-1 group-title="{topic_name}"{logo_attr},{ch_name}')
                if headers.get('User-Agent'):
                    m3u_lines.append(f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}')
                if headers.get('Referer'):
                    m3u_lines.append(f'#EXTVLCOPT:http-referrer={headers["Referer"]}')
                
                m3u_lines.append(final_url)

    # حفظ الملف
    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print("✅ Playlist saved to playlist.m3u8")

if __name__ == "__main__":
    main()

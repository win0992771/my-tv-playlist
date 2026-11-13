import json
import base64
import sys
import os
from curl_cffi import requests as curl_requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

with open("playlist.m3u8", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")

BASE_URL = "http://live.publicdataroute.cc/api/live/livedrama/v13.0.0"
HEADERS = {
    "User-Agent": "okhttp/3.12.13", 
    "Content-Type": "application/json",
    "Accept": "application/json"
}
KEY = b"fedcba9876543210"

# ==== إعدادات البروكسي ====
# يتم تمريرها من GitHub Secrets أو المتغيرات
PROXY_URL = os.environ.get("PROXY_URL", "")  # مثال: http://user:pass@ip:port
PROXY_TYPE = os.environ.get("PROXY_TYPE", "http") # http أو socks5

# ==== بصمة OkHttp ====
OKHTTP4_ANDROID10_JA3 = "771,4865-4866-4867-49195-49196-52393-49199-49200-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-51-45-43-21,29-23-24,0"
OKHTTP4_ANDROID10_AKAMAI = "4:16777216|16711681|0|m,p,a,s"
EXTRA_FP = {
    "tls_signature_algorithms": [
        "ecdsa_secp256r1_sha256", "rsa_pss_rsae_sha256", "rsa_pkcs1_sha256",
        "ecdsa_secp384r1_sha384", "rsa_pss_rsae_sha384", "rsa_pkcs1_sha384",
        "rsa_pss_rsae_sha512", "rsa_pkcs1_sha512", "rsa_pkcs1_sha1",
    ]
}

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
    
    # إعداد البروكسي إذا تم تمريره
    proxies = None
    if PROXY_URL:
        proxies = {
            "http": PROXY_URL,
            "https": PROXY_URL
        }
        print(f"[Proxy] Using: {PROXY_URL.split('@')[-1] if '@' in PROXY_URL else PROXY_URL}")
    
    try:
        r = curl_requests.post(
            url, 
            headers=HEADERS, 
            json=payload or {}, 
            timeout=30,
            ja3=OKHTTP4_ANDROID10_JA3,
            akamai=OKHTTP4_ANDROID10_AKAMAI,
            extra_fp=EXTRA_FP,
            proxies=proxies
        )
        print(f"[{endpoint}] Status Code: {r.status_code}")
        print(f"[{endpoint}] Raw Response: {r.text[:200]}") 
        
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
        print("FAILED: Still blocked by server.")
        sys.exit(0) 

    m3u_lines = ["#EXTM3U"]
    for topic in topics_data.get("live_topics", []):
        topic_id = topic.get("id_topic")
        topic_name = topic.get("name_topic", "Unknown")
        if not topic_id: continue
        
        print(f"Fetching channels for topic: {topic_name}")
        channels_data = api_request("getLiveByTopic", {"id_topic": topic_id})
        if not channels_data or "live" not in channels_data: continue

        for ch in channels_data["live"]:
            ch_id = ch.get("id_live")
            ch_name = ch.get("name", "Unknown")
            ch_logo = ch.get("img_url", "")
            if not ch_id: continue

            print(f"Fetching stream for: {ch_name}")
            stream_data = api_request("getLiveAllStreamsById", {"id_live": ch_id})
            if not stream_data: continue

            final_url = None
            headers = {}
            if "data" in stream_data and "url" in stream_data["data"]:
                raw_url = stream_data["data"]["url"]
                decrypted_raw = decrypt_data(raw_url)
                try:
                    inner_json = json.loads(decrypted_raw)
                    if "url" in inner_json:
                        final_url = inner_json["url"]
                        headers = inner_json.get("headers", {})
                except:
                    final_url = decrypted_raw

            if final_url:
                logo_attr = f' tvg-logo="{ch_logo}"' if ch_logo else ""
                m3u_lines.append(f'#EXTINF:-1 group-title="{topic_name}"{logo_attr},{ch_name}')
                if headers.get('User-Agent'):
                    m3u_lines.append(f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}')
                if headers.get('Referer'):
                    m3u_lines.append(f'#EXTVLCOPT:http-referrer={headers["Referer"]}')
                m3u_lines.append(final_url)

    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    print("✅ Playlist saved to playlist.m3u8")

if __name__ == "__main__":
    main()

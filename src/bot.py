import os
import sys
import json
import urllib.request
import urllib.parse
import tempfile
import re

sys.path.insert(0, os.path.dirname(__file__))
from config import API_URL
from state import load as load_state, save as save_state
from downloader import download, compress, detect_platform

BOUNDARY = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

def encode_multipart(fields, files):
    body = b""
    for key, value in fields.items():
        body += f"--{BOUNDARY}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()
    for key, (filename, fileobj, content_type) in files.items():
        body += f"--{BOUNDARY}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += fileobj.read()
        body += b"\r\n"
    body += f"--{BOUNDARY}--\r\n".encode()
    return body

def api(method, data=None, files=None):
    url = f"{API_URL}/{method}"
    if files:
        body = encode_multipart(data or {}, files)
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={BOUNDARY}")
        req.add_header("Content-Length", str(len(body)))
    elif data:
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    else:
        req = urllib.request.Request(url)

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        print(f"⚠️ HTTP {e.code}: {text[:200]}")
        return {"ok": False, "error": text}

def get_updates(offset):
    data = {"offset": offset, "timeout": 10, "allowed_updates": json.dumps(["message"])}
    result = api("getUpdates", data)
    if result.get("ok"):
        return result["result"]
    return []

def send_message(chat_id, text):
    api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def send_video(chat_id, filepath):
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        result = api("sendVideo", {"chat_id": chat_id, "supports_streaming": True}, {"video": (filename, f, "video/mp4")})
    return result.get("ok", False)

def send_document(chat_id, filepath):
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        result = api("sendDocument", {"chat_id": chat_id}, {"document": (filename, f)})
    return result.get("ok", False)

def extract_url(text):
    urls = re.findall(r"https?://[^\s]+", text)
    return urls[0] if urls else None

def process_message(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    url = extract_url(text)
    if not url:
        send_message(chat_id, "👋 أرسل رابط فيديو من يوتيوب، تيك توك، إنستغرام، تويتر، أو فيسبوك")
        return True

    send_message(chat_id, "⏳ جاري تحميل الفيديو... الرجاء الانتظار")
    platform = detect_platform(url)
    print(f"🌐 المنصة: {platform} | الرابط: {url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            filepath = download(url, tmpdir)
            file_size = os.path.getsize(filepath)
            print(f"📦 حجم الملف: {file_size / 1024 / 1024:.1f}MB")

            if file_size > 45 * 1024 * 1024:
                send_message(chat_id, "⚠️ الفيديو كبير جداً (>45MB)، جاري ضغطه...")
                filepath = compress(filepath)
                file_size = os.path.getsize(filepath)

            if file_size > 50 * 1024 * 1024:
                send_message(chat_id, "❌ الفيديو أكبر من 50MB حتى بعد الضغط. Telegram لا يدعم رفعه.")
                return True

            ext = os.path.splitext(filepath)[1].lower()
            video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".gif"}
            success = send_video(chat_id, filepath) if ext in video_exts else send_document(chat_id, filepath)

            if success:
                send_message(chat_id, "✅ تم التحميل بنجاح!")
            else:
                send_message(chat_id, "⚠️ تم التحميل لكن فشل الرفع. حاول مرة أخرى.")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ خطأ: {error_msg}")
            if "413" in error_msg or "filesize" in error_msg.lower():
                send_message(chat_id, "❌ الفيديو كبير جداً (حد 50MB لرفع Telegram)")
            elif "Private video" in error_msg or "private" in error_msg.lower():
                send_message(chat_id, "❌ هذا الفيديو خاص أو محمي")
            elif "Unsupported" in error_msg or "not supported" in error_msg.lower():
                send_message(chat_id, "❌ هذا الرابط غير مدعوم حالياً")
            else:
                send_message(chat_id, f"❌ فشل التحميل: {error_msg[:150]}")

    return True

def main():
    print("🤖 بوت تحميل الفيديوهات يعمل...")

    state = load_state()
    offset = state.get("last_update_id", 0) + 1
    processed = set(state.get("processed", []))

    updates = get_updates(offset)
    if not updates:
        print("📭 لا توجد رسائل جديدة")
        return

    print(f"📨 عدد الرسائل الجديدة: {len(updates)}")
    max_id = offset - 1

    for update in updates:
        update_id = update["update_id"]
        max_id = max(max_id, update_id)
        msg = update.get("message")
        if not msg:
            continue

        key = f"{msg['chat']['id']}_{msg['message_id']}"
        if key in processed:
            continue

        text = msg.get("text", "")
        if not text:
            continue

        print(f"💬 من {msg['chat']['id']}: {text[:60]}...")
        process_message(msg)
        processed.add(key)

    state["last_update_id"] = max_id
    state["processed"] = list(processed)[-500:]
    save_state(state)
    print("✅ تم حفظ الحالة")

if __name__ == "__main__":
    main()

import os
import subprocess
import shutil
import re

PLATFORMS = {
    "youtube": r"(youtube\.com|youtu\.be)",
    "tiktok": r"(tiktok\.com)",
    "instagram": r"(instagram\.com)",
    "twitter": r"(twitter\.com|x\.com)",
    "facebook": r"(facebook\.com|fb\.com)",
}

def detect_platform(url):
    for name, pattern in PLATFORMS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return name
    return "unknown"

def download(url, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    yt_dlp = shutil.which("yt-dlp") or "yt-dlp"
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    cmd = [
        yt_dlp,
        "-f", "best[filesize<45M]/best",
        "--max-filesize", "45M",
        "--no-playlist",
        "--no-warnings",
        "--print", "after_move:filepath",
        "-o", output_template,
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        raise Exception(error)

    filepath = result.stdout.strip().split("\n")[-1]
    if not filepath or not os.path.exists(filepath):
        raise Exception("لم يتم العثور على الملف المحمل")
    return filepath

def compress(filepath):
    output = filepath.rsplit(".", 1)[0] + "_compressed.mp4"
    cmd = [
        "ffmpeg", "-i", filepath,
        "-vf", "scale=iw/2:ih/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "28",
        "-c:a", "aac", "-b:a", "64k",
        "-y", output,
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if os.path.exists(output):
        os.remove(filepath)
        return output
    return filepath

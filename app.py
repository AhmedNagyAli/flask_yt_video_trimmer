from flask import Flask, render_template, request, send_from_directory
import subprocess
import uuid
import os
import re
import unicodedata
import json

app = Flask(__name__)
OUTPUT_DIR = "static/videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def safe_name(filename):
    # Normalize unicode (NFKD form) and remove unwanted characters  except arabic
    nfkd_form = unicodedata.normalize('NFKD', filename)
    safe_str = re.sub(r"[^\w\s\-ء-ي]", "", nfkd_form)
    safe_str = re.sub(r"\s+", "_", safe_str)
    return safe_str
def format_time_for_filename(t):
    return re.sub(r'[:.]', '', t) if t else ""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["youtube_url"]
        result = subprocess.run(["yt-dlp", "-F", url], capture_output=True, text=True)
        formats = []
        for line in result.stdout.splitlines():
            if line.strip() and line[0].isdigit():
                parts = line.split()
                format_id = parts[0]
                resolution = parts[2] if len(parts) > 2 else 'Unknown'
                formats.append({"id": format_id, "resolution": resolution})
        return render_template("download.html", url=url, formats=formats)
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    format_id = request.form["format_id"]
    start_time = request.form.get("start_time", "")
    end_time = request.form.get("end_time", "")

    # Get video title
    result_title = subprocess.run(
        ["yt-dlp", "--get-title", url],
        capture_output=True, text=True
    )
    video_title = result_title.stdout.strip()
    safe_title = safe_name(video_title)

    # Create folder for this video
    folder_path = os.path.join(OUTPUT_DIR, safe_title)
    os.makedirs(folder_path, exist_ok=True)

    # Get format info in JSON to get both audio and video URLs
    result_info = subprocess.run(
        ["yt-dlp", "-f", format_id, "-j", url],
        capture_output=True, text=True
    )
    info = json.loads(result_info.stdout)

    video_url = None
    audio_url = None

    # Find requested video format URL
    for f in info.get("formats", []):
        if str(f.get("format_id")) == format_id:
            if f.get("acodec") == "none":
                video_url = f.get("url")
            elif f.get("vcodec") == "none":
                audio_url = f.get("url")
            else:
                video_url = f.get("url")
                audio_url = None
            break

    # If video only, find best audio format to merge
    if audio_url is None:
        audio_formats = [f for f in info.get("formats", []) if f.get("acodec") != "none" and f.get("vcodec") == "none"]
        if audio_formats:
            audio_formats.sort(key=lambda x: (x.get("abr") or 0), reverse=True)
            audio_url = audio_formats[0].get("url")

    if video_url is None:
        return "Video URL not found", 400

    # Download video and audio to temp files
    video_path = os.path.join(folder_path, "video.mp4")
    audio_path = os.path.join(folder_path, "audio.m4a") if audio_url else None

    subprocess.run(["ffmpeg", "-y", "-i", video_url, "-c", "copy", video_path])

    if audio_url:
        subprocess.run(["ffmpeg", "-y", "-i", audio_url, "-c", "copy", audio_path])

    # Prepare trimming suffix for filename
    def format_time_for_filename(t):
        return re.sub(r'[:.]', '', t) if t else ""

    start_str = format_time_for_filename(start_time)
    end_str = format_time_for_filename(end_time)
    trimmed_suffix = ""
    if start_str or end_str:
        trimmed_suffix = f"_start-{start_str}_end-{end_str}"

    output_filename = f"{safe_title}{trimmed_suffix}.mp4"
    output_path = os.path.join(folder_path, output_filename)

    # Calculate duration for trimming
    start_sec = None
    end_sec = None
    try:
        start_sec = float(start_time) if start_time else None
        end_sec = float(end_time) if end_time else None
    except ValueError:
        pass

    duration = None
    if start_sec is not None and end_sec is not None and end_sec > start_sec:
        duration = end_sec - start_sec

    # Build ffmpeg command to trim and merge (seek after inputs for accurate sync)
    ffmpeg_cmd = ["ffmpeg", "-y"]
    ffmpeg_cmd.extend(["-i", video_path])
    if audio_path:
        ffmpeg_cmd.extend(["-i", audio_path])

    if start_sec is not None:
        ffmpeg_cmd.extend(["-ss", start_time])

    if duration is not None:
        ffmpeg_cmd.extend(["-t", str(duration)])

    if audio_path:
        ffmpeg_cmd.extend([
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-avoid_negative_ts", "make_zero",
        ])
    else:
        ffmpeg_cmd.extend(["-c", "copy"])

    ffmpeg_cmd.append(output_path)

    subprocess.run(ffmpeg_cmd)

    # Clean up temp files
    os.remove(video_path)
    if audio_path:
        os.remove(audio_path)

    relative_path = f"videos/{safe_title}/{output_filename}"
    return render_template("result.html", filename=relative_path)

@app.route("/videos/<filename>")
def serve_video(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, after_this_request, render_template, request, send_from_directory
import subprocess
import os
import re
import unicodedata
import json
import yt_dlp
from urllib.parse import urlparse
import threading

app = Flask(__name__)
OUTPUT_DIR = "static/videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def safe_name(filename):
    nfkd_form = unicodedata.normalize('NFKD', filename)
    safe_str = re.sub(r"[^\w\s\-ء-ي]", "", nfkd_form)
    safe_str = re.sub(r"\s+", "_", safe_str)
    return safe_str

def format_time_for_filename(t):
    return re.sub(r'[:.]', '', t) if t else ""

#validate input youtube video url
def is_valid_youtube_url(url):
    parsed = urlparse(url)
    return parsed.netloc in ["www.youtube.com", "youtube.com", "youtu.be"]

def get_preview_url(youtube_url, preferred_resolution='480p'):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        formats = info.get("formats", [])
        for fmt in formats:
            if (fmt.get('ext') == 'mp4' and
                fmt.get('acodec') != 'none' and
                fmt.get('vcodec') != 'none' and
                fmt.get('format_note') == preferred_resolution):
                return fmt.get('url')
        for fmt in formats:
            if (fmt.get('ext') == 'mp4' and
                fmt.get('acodec') != 'none' and
                fmt.get('vcodec') != 'none'):
                return fmt.get('url')
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["youtube_url"]
        
        if not url:
            return render_template("index.html", error="YouTube URL is required.")

        if not is_valid_youtube_url(url):
            return render_template("index.html", error="❌ Invalid YouTube URL. Please enter a valid one.")

        # try:
        #     with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        #         info = ydl.extract_info(url, download=False)
        # except Exception as e:
        #     return f"Error fetching video info: {str(e)}", 500
        metadata_result = subprocess.run(["yt-dlp", "-j", url], capture_output=True, text=True)
        metadata = json.loads(metadata_result.stdout)
        video_length_seconds = metadata.get("duration", 0)
        video_data = get_preview_url(url)
        result = subprocess.run(["yt-dlp", "-F", url], capture_output=True, text=True)
        formats = []
        for line in result.stdout.splitlines():
            if line.strip() and line[0].isdigit():
                if "audio" in line.lower():
                    continue
                parts = line.split()
                format_id = parts[0]
                resolution = parts[2] if len(parts) > 2 else 'Unknown'
                formats.append({"id": format_id, "resolution": resolution})
        return render_template("download.html",
                               url=url,
                               formats=formats,
                               video_length=video_length_seconds,
                               preview_url=video_data)
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
    try:
        url = request.form["url"]
        format_id = request.form["format_id"]
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")

        # Get video title and create safe filename
        result_title = subprocess.run(["yt-dlp", "--get-title", url], capture_output=True, text=True)
        if result_title.returncode != 0:
            return "Error getting video title", 400
        video_title = result_title.stdout.strip()
        safe_title = safe_name(video_title)

        # Create output directory
        folder_path = os.path.join(OUTPUT_DIR, safe_title)
        os.makedirs(folder_path, exist_ok=True)

        # Get video info
        result_info = subprocess.run(["yt-dlp", "-f", format_id, "-j", url], capture_output=True, text=True)
        if result_info.returncode != 0:
            return "Error getting video info", 400
        info = json.loads(result_info.stdout)

        # Extract video and audio URLs
        video_url = None
        audio_url = None
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

        if video_url is None:
            return "Video URL not found", 400

        # Get best audio if needed
        if audio_url is None:
            audio_formats = [f for f in info.get("formats", []) if f.get("acodec") != "none" and f.get("vcodec") == "none"]
            if audio_formats:
                audio_formats.sort(key=lambda x: (x.get("abr") or 0), reverse=True)
                audio_url = audio_formats[0].get("url")

        # Prepare filenames
        start_str = format_time_for_filename(start_time)
        end_str = format_time_for_filename(end_time)
        trimmed_suffix = f"_start-{start_str}_end-{end_str}" if start_str or end_str else ""
        output_filename = f"{safe_title}{trimmed_suffix}.mp4"
        output_path = os.path.join(folder_path, output_filename)

        # Parse time values
        try:
            start_sec = float(start_time) if start_time else None
            end_sec = float(end_time) if end_time else None
        except ValueError:
            start_sec = end_sec = None

        duration = end_sec - start_sec if start_sec is not None and end_sec is not None and end_sec > start_sec else None

        # Build FFmpeg command
        ffmpeg_cmd = ["ffmpeg", "-y"]
        
        # Input URLs directly (no need to download separately)
        ffmpeg_cmd.extend(["-i", video_url])
        if audio_url:
            ffmpeg_cmd.extend(["-i", audio_url])

        # Apply trimming
        if start_sec is not None:
            ffmpeg_cmd.extend(["-ss", str(start_sec)])
        if duration is not None:
            ffmpeg_cmd.extend(["-t", str(duration)])

        # Output settings
        ffmpeg_cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-movflags", "+faststart"
        ])
        
        if audio_url:
            ffmpeg_cmd.extend([
                "-c:a", "aac",
                "-b:a", "128k",
                "-map", "0:v:0",
                "-map", "1:a:0"
            ])
        else:
            ffmpeg_cmd.extend(["-c:a", "copy"])

        ffmpeg_cmd.append(output_path)

        # Run FFmpeg
        result = subprocess.run(ffmpeg_cmd, stderr=subprocess.PIPE)
        if result.returncode != 0:
            app.logger.error(f"FFmpeg failed: {result.stderr.decode()}")
            return "Error processing video", 500

        if not os.path.exists(output_path):
            return "Error: Output file was not created", 500

        relative_path = f"videos/{safe_title}/{output_filename}"
        return render_template("result.html", filename=relative_path)

    except Exception as e:
        app.logger.error(f"Error in download route: {str(e)}")
        return "An error occurred while processing your request", 500



def delayed_delete(filepath, delay=10):
    def delete_file():
        import time
        time.sleep(delay)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                app.logger.info(f"Successfully deleted {filepath}")
        except Exception as e:
            app.logger.error(f"Error deleting file: {str(e)}")
    
    thread = threading.Thread(target=delete_file)
    thread.daemon = True
    thread.start()


@app.route("/videos/<path:filename>")
def serve_video(filename):
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404

    try:
        # Start deletion in background after delay
        delayed_delete(file_path)
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Error serving video: {str(e)}")
        return "Internal server error", 500
    
    
    
# @app.route("/videos/<filename>")
# def serve_video(filename):
#     file_path = os.path.join(OUTPUT_DIR, filename)

#     @after_this_request
#     def remove_file(response):
#         try:
#             os.remove(file_path)
#         except Exception as e:
#             app.logger.error(f"Error deleting file {file_path}: {e}")
#         return response

#     return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT",6000))
    app.run(host="0.0.0.0",port=port)

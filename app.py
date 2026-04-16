from flask import Flask, request, redirect, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
import os
import subprocess
import shlex

# Configuration Paths
MEDIA_FOLDER = "/home/pi/magic-frame/media"
STEALTH_FOLDER = "/home/pi/magic-frame/stealth_media"
MODE_FILE = "/home/pi/magic-frame/mode.txt"

app = Flask(__name__)

# --- UI with Gallery, FFmpeg Loader, mDNS, and Previews ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Magic Frame Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; padding: 20px; max-width: 600px; margin: auto; line-height: 1.6; }
        button { padding: 10px; margin: 5px 0; cursor: pointer; border: none; border-radius: 4px; }
        input[type="file"], input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; border: 1px solid #ccc; }
        .section { border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 20px; }
        .btn-green { background-color: #4CAF50; color: white; width: 100%; font-weight: bold; }
        .btn-gray { background-color: #e7e7e7; width: 48%; }
        .btn-red { background-color: #ff4d4d; color: white; padding: 5px 10px; font-size: 0.8em; }
        .file-list { list-style: none; padding: 0; }
        .file-item { display: flex; justify-content: space-between; align-items: center; background: #f9f9f9; margin: 5px 0; padding: 8px; border-radius: 4px; border: 1px solid #ddd; }
        .file-link { color: #0066cc; text-decoration: none; font-weight: bold; word-break: break-all; margin-right: 10px; }
        .file-link:hover { text-decoration: underline; }
        .folder-label { font-weight: bold; color: #555; margin-top: 10px; display: block; }
        #loading { display: none; color: #d9534f; font-weight: bold; text-align: center; margin-top: 10px; }
    </style>
    <script>
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('btn-normal').disabled = true;
            document.getElementById('btn-stealth').disabled = true;
        }
    </script>
</head>
<body>
    <div class="section">
        <h2>Upload Media</h2>
        <p><small>Videos are automatically optimized for the Pi. This may take a minute!</small></p>
        <form method="post" enctype="multipart/form-data" onsubmit="showLoading()">
            <input type="file" name="file" required>
            <button id="btn-normal" name="upload_type" value="normal" class="btn-gray">To Normal</button>
            <button id="btn-stealth" name="upload_type" value="stealth" class="btn-gray" style="background-color: #d1d1d1;">To Stealth</button>
            <div id="loading">Processing media... Please wait.</div>
        </form>
    </div>

    <div class="section">
        <h2>Gallery (Manage Files)</h2>
        
        <span class="folder-label">Normal Media:</span>
        <ul class="file-list">
            {% for file in normal_files %}
            <li class="file-item">
                <a href="/view/media/{{ file }}" target="_blank" class="file-link">🖼️ {{ file }}</a>
                <a href="/delete/media/{{ file }}" onclick="return confirm('Delete {{ file }}?')"><button class="btn-red">Delete</button></a>
            </li>
            {% else %}
            <li class="file-item" style="color:#999;">Folder is empty</li>
            {% endfor %}
        </ul>

        <span class="folder-label">Stealth Media:</span>
        <ul class="file-list">
            {% for file in stealth_files %}
            <li class="file-item">
                <a href="/view/stealth_media/{{ file }}" target="_blank" class="file-link">🖼️ {{ file }}</a>
                <a href="/delete/stealth_media/{{ file }}" onclick="return confirm('Delete {{ file }}?')"><button class="btn-red">Delete</button></a>
            </li>
            {% else %}
            <li class="file-item" style="color:#999;">Folder is empty</li>
            {% endfor %}
        </ul>
    </div>

    <div class="section">
        <h2>Controls</h2>
        <a href="/mode/normal"><button class="btn-gray" style="width:100%;">Switch to Normal Mode</button></a>
        <a href="/mode/stealth"><button class="btn-gray" style="width:100%;">Switch to Stealth Mode</button></a>
    </div>

    <div class="section">
        <h2>Connect Frame to Home Wi-Fi</h2>
        <p><small>Current Hostname: <b>http://magic-frame.local:5000</b></small></p>
        <form action="/wifi" method="post">
            SSID: <input type="text" name="ssid" placeholder="e.g. BELL030" required>
            Password: <input type="password" name="password" required>
            <button type="submit" class="btn-green">Apply & Reboot</button>
        </form>
    </div>
</body>
</html>
"""

# ---------------- UPLOAD & GALLERY ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        upload_type = request.form.get("upload_type")
        
        if file and file.filename:
            filename = secure_filename(file.filename)
            target_folder = STEALTH_FOLDER if upload_type == "stealth" else MEDIA_FOLDER
            
            base_name, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            video_extensions = [
                '.mp4', '.mov', '.avi', '.mkv', '.m4v', 
                '.webm', '.flv', '.wmv', '.mpg', '.mpeg', 
                '.3gp', '.hevc', '.ts', '.m2ts'
            ]
            
            if ext in video_extensions:
                temp_path = os.path.join(target_folder, f"temp_{filename}")
                final_path = os.path.join(target_folder, f"{base_name}.mp4")
                file.save(temp_path)
                
                print(f"Processing video: {filename}...")
                
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", temp_path,
                    "-vf", "scale=960:-2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast", "-crf", "30",
                    "-threads", "1", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    final_path
                ]
                
                try:
                    subprocess.run(ffmpeg_cmd, check=True)
                    os.remove(temp_path)
                    print("Video processed successfully!")
                except subprocess.CalledProcessError as e:
                    print(f"FFmpeg failed: {e}")
                    os.rename(temp_path, os.path.join(target_folder, filename))
            else:
                path = os.path.join(target_folder, filename)
                file.save(path)

            os.system("sudo systemctl restart videoframe.service")
            return redirect("/")

    normal_files = os.listdir(MEDIA_FOLDER) if os.path.exists(MEDIA_FOLDER) else []
    stealth_files = os.listdir(STEALTH_FOLDER) if os.path.exists(STEALTH_FOLDER) else []
    
    normal_files.sort()
    stealth_files.sort()
    
    return render_template_string(HTML, normal_files=normal_files, stealth_files=stealth_files)

# ---------------- RAW DATA PROVIDER ----------------
@app.route("/raw/<folder>/<filename>")
def raw_file(folder, filename):
    """Feeds the actual bytes of the file to the media player."""
    base_path = MEDIA_FOLDER if folder == "media" else STEALTH_FOLDER
    return send_from_directory(base_path, secure_filename(filename))

# ---------------- MEDIA PLAYER PREVIEW ----------------
@app.route("/view/<folder>/<filename>")
def view_file(folder, filename):
    """Builds a mini web page to force the browser to play/show the media."""
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in ['.mp4', '.mov', '.webm', '.m4v']
    
    file_url = f"/raw/{folder}/{filename}"
    
    if is_video:
        media_html = f'<video controls autoplay playsinline style="max-width:100%; max-height:70vh; border-radius:8px;"><source src="{file_url}"></video>'
    else:
        media_html = f'<img src="{file_url}" style="max-width:100%; max-height:70vh; border-radius:8px; box-shadow: 0px 4px 15px rgba(0,0,0,0.5);">'

    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Preview: {filename}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body style="background-color: #1a1a1a; color: white; text-align: center; font-family: sans-serif; padding: 20px; margin: 0;">
            <h3 style="color: #ccc; word-break: break-all;">{filename}</h3>
            {media_html}
            <br><br>
            <button onclick="window.close()" style="background-color: #4CAF50; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 5px; cursor: pointer;">
                Close Preview
            </button>
        </body>
    </html>
    """

# ---------------- DELETE ----------------
@app.route("/delete/<folder>/<filename>")
def delete_file(folder, filename):
    base_path = MEDIA_FOLDER if folder == "media" else STEALTH_FOLDER
    file_path = os.path.join(base_path, secure_filename(filename))

    if os.path.exists(file_path):
        os.remove(file_path)
        os.system("sudo systemctl restart videoframe.service")
    
    return redirect("/")

# ---------------- MODE SWITCH ----------------
@app.route("/mode/<mode>")
def mode(mode):
    if mode in ["normal", "stealth"]:
        with open(MODE_FILE, "w") as f:
            f.write(mode)
        os.system("sudo systemctl restart videoframe.service")
    return redirect("/")

# ---------------- WIFI SETUP ----------------
@app.route("/wifi", methods=["POST"])
def wifi():
    ssid = request.form.get("ssid")
    password = request.form.get("password")

    if ssid and password:
        safe_ssid = shlex.quote(ssid)
        safe_pw = shlex.quote(password)

        manage_cmd = "sudo nmcli device set wlan0 managed yes"
        clean_cmd = f"sudo nmcli connection delete {safe_ssid} || true"
        add_cmd = f"sudo nmcli connection add type wifi ifname wlan0 con-name {safe_ssid} ssid {safe_ssid}"
        mod_cmd = (
            f"sudo nmcli connection modify {safe_ssid} "
            f"wifi-sec.key-mgmt wpa-psk wifi-sec.psk {safe_pw} "
            f"connection.autoconnect-priority 100"
        )
        up_cmd = f"sudo nmcli connection up {safe_ssid}"

        wifi_cmd = f"{clean_cmd} && {add_cmd} && {mod_cmd} && {up_cmd}"
        fallback_cmd = "sudo nmcli connection up Hotspot"

        full_command = (
            f"{manage_cmd} && "
            f"({wifi_cmd} && sleep 3 && sudo reboot) || "
            f"({fallback_cmd})"
        )

        print(f"Executing: {full_command}")
        subprocess.Popen(full_command, shell=True)

        return f"""
        <html>
            <head>
                <meta http-equiv="refresh" content="35;url=http://magic-frame.local:5000">
            </head>
            <body style="font-family:sans-serif; text-align:center; padding-top:100px;">
                <h1>Applying Settings...</h1>
                <p>The Pi is joining <b>{ssid}</b>.</p>
                <p>Please wait 35 seconds for the reboot...</p>
                <p>Then your phone should automatically redirect to:</p>
                <p><b><a href="http://magic-frame.local:5000">http://magic-frame.local:5000</a></b></p>
                <p><small>Ensure your phone switches to the same Wi-Fi!</small></p>
            </body>
        </html>
        """
    return redirect("/")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    os.makedirs(MEDIA_FOLDER, exist_ok=True)
    os.makedirs(STEALTH_FOLDER, exist_ok=True)

    if not os.path.exists(MODE_FILE):
        with open(MODE_FILE, "w") as f:
            f.write("normal")

    print("Starting Magic Frame Flask server on port 5000...")
    app.run(host="0.0.0.0", port=5000)

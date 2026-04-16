from flask import Flask, request, redirect, render_template_string
from werkzeug.utils import secure_filename
import os
import subprocess
import shlex

# Configuration Paths
MEDIA_FOLDER = "/home/pi/magic-frame/media"
STEALTH_FOLDER = "/home/pi/magic-frame/stealth_media"
MODE_FILE = "/home/pi/magic-frame/mode.txt"

app = Flask(__name__)

# --- UI with mDNS Support ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Magic Frame Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; padding: 20px; max-width: 500px; margin: auto; line-height: 1.6; }
        button { padding: 12px; margin: 5px 0; width: 100%; cursor: pointer; border: none; border-radius: 4px; }
        input { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; border: 1px solid #ccc; }
        .section { border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 20px; }
        .btn-green { background-color: #4CAF50; color: white; font-weight: bold; }
        .btn-gray { background-color: #e7e7e7; }
    </style>
</head>
<body>
    <div class="section">
        <h2>Upload Media</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <button name="upload_type" value="normal" class="btn-gray">Upload to Normal</button>
            <button name="upload_type" value="stealth" class="btn-gray" style="background-color: #d1d1d1;">Upload to Stealth</button>
        </form>
    </div>

    <div class="section">
        <h2>Controls</h2>
        <a href="/mode/normal"><button class="btn-gray">Switch to Normal Mode</button></a>
        <a href="/mode/stealth"><button class="btn-gray">Switch to Stealth Mode</button></a>
    </div>

    <div class="section">
        <h2>Connect Frame to Home Wi-Fi</h2>
        <p><small>Current Hostname: <b>http://magic-frame.local:5000</b></small></p>
        <form action="/wifi" method="post">
            SSID: <input name="ssid" placeholder="e.g. BELL030" required>
            Password: <input name="password" type="password" required>
            <button type="submit" class="btn-green">Apply & Reboot</button>
        </form>
    </div>
</body>
</html>
"""

# ---------------- UPLOAD ----------------
@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        upload_type = request.form.get("upload_type")
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(STEALTH_FOLDER if upload_type == "stealth" else MEDIA_FOLDER, filename)
            file.save(path)
            os.system("sudo systemctl restart videoframe.service")
    return render_template_string(HTML)

# ---------------- MODE SWITCH ----------------
@app.route("/mode/<mode>")
def mode(mode):
    if mode in ["normal", "stealth"]:
        with open(MODE_FILE, "w") as f:
            f.write(mode)
        os.system("sudo systemctl restart videoframe.service")
    return redirect("/")

# ---------------- WIFI SETUP (The Final Version) ----------------
@app.route("/wifi", methods=["POST"])
def wifi():
    ssid = request.form.get("ssid")
    password = request.form.get("password")

    if ssid and password:
        safe_ssid = shlex.quote(ssid)
        safe_pw = shlex.quote(password)

        # 1. Unlock radio
        manage_cmd = "sudo nmcli device set wlan0 managed yes"

        # 2. Manual Profile Builder
        # Priority 100 ensures BELL030 beats Hotspot (10)
        clean_cmd = f"sudo nmcli connection delete {safe_ssid} || true"
        add_cmd = f"sudo nmcli connection add type wifi ifname wlan0 con-name {safe_ssid} ssid {safe_ssid}"
        mod_cmd = (
            f"sudo nmcli connection modify {safe_ssid} "
            f"wifi-sec.key-mgmt wpa-psk wifi-sec.psk {safe_pw} "
            f"connection.autoconnect-priority 100"
        )
        up_cmd = f"sudo nmcli connection up {safe_ssid}"

        wifi_cmd = f"{clean_cmd} && {add_cmd} && {mod_cmd} && {up_cmd}"

        # 3. Fallback
        fallback_cmd = "sudo nmcli connection up Hotspot"

        # 4. Logic Chain
        full_command = (
            f"{manage_cmd} && "
            f"({wifi_cmd} && sleep 3 && sudo reboot) || "
            f"({fallback_cmd})"
        )

        print(f"Executing: {full_command}")
        subprocess.Popen(full_command, shell=True)

        # Redirect user to the new .local address after 35 seconds
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
                <p><b><a href="http://magicframe.local:5000">http://magic-frame.local:5000</a></b></p>
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

from flask import Flask, request, redirect, render_template_string
from werkzeug.utils import secure_filename
import os

MEDIA_FOLDER = "/home/pi/magic-frame/media"
STEALTH_FOLDER = "/home/pi/magic-frame/stealth_media"
MODE_FILE = "/home/pi/magic-frame/mode.txt"

app = Flask(__name__)

HTML = """
<h2>Upload Media</h2>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="file">
  <br><br>
  <button name="upload_type" value="normal">Upload to Normal</button>
  <button name="upload_type" value="stealth">Upload to Stealth</button>
</form>

<hr>

<h2>Controls</h2>
<form action="/mode/normal"><button>Normal Mode</button></form>
<form action="/mode/stealth"><button>Stealth Mode</button></form>

<hr>

<h2>Connect to WiFi</h2>
<form action="/wifi" method="post">
  SSID: <input name="ssid"><br><br>
  Password: <input name="password" type="password"><br><br>
  <button type="submit">Connect</button>
</form>
"""

# ---------------- UPLOAD ----------------
@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        upload_type = request.form.get("upload_type")

        if file and file.filename:
            filename = secure_filename(file.filename)

            if upload_type == "stealth":
                path = os.path.join(STEALTH_FOLDER, filename)
            else:
                path = os.path.join(MEDIA_FOLDER, filename)

            file.save(path)

            # restart player
            os.system("sudo systemctl restart videoframe.service")

    return render_template_string(HTML)

# ---------------- MODE SWITCH ----------------
@app.route("/mode/<mode>")
def mode(mode):
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
        config = f'''
network={{
    ssid="{ssid}"
    psk="{password}"
}}
'''

        # append wifi config
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
            f.write(config)

        # disable hotspot services
        os.system("sudo systemctl disable hostapd")
        os.system("sudo systemctl disable dnsmasq")

        # reboot to apply
        os.system("sudo reboot")

    return redirect("/")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000)

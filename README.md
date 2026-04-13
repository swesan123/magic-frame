# magic-frame

Digital frame playback for Raspberry Pi (mpv, fullscreen, looping). Upload UI comes later.

## Phase 1: test video on the display

1. **Install mpv**

   ```bash
   sudo apt update && sudo apt install -y mpv
   ```

2. **Portrait (recommended)**  
   On Raspberry Pi OS, set rotation in `/boot/firmware/config.txt` (Bookworm) or `/boot/config.txt`:

   - `display_hdmi_rotate=1` (try `2` or `3` if orientation is wrong)

   Reboot after editing.

3. **Fallback rotation (mpv)**  
   If you have not rotated in firmware:

   ```bash
   export MAGIC_FRAME_MPV_OPTS="--video-rotate=90"
   ```

4. **Add media**  
   Put `.mp4`, `.mkv`, `.webm`, `.jpg`, `.jpeg`, `.png`, or `.gif` files in [`videos/`](videos/).

5. **Run manually** (from a desktop session / auto-login to desktop):

   ```bash
   cd /home/pi/magic-frame
   ./start_frame.sh
   ```

   Stop with Ctrl+C. To simulate “reload after new files” (for later upload integration):

   ```bash
   ./restart_player.sh
   ```

6. **Optional: start on boot**

   ```bash
   sudo cp deploy/magic-frame-player.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now magic-frame-player.service
   ```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `MAGIC_FRAME_VIDEO_DIR` | Media folder (default: `videos/` next to the script) |
| `MAGIC_FRAME_MPV_OPTS` | Extra mpv arguments (e.g. `--video-rotate=90`) |
| `MAGIC_FRAME_IMAGE_DURATION` | Seconds per still image (default: `8`) |
| `DISPLAY` | X display (default `:0`) |

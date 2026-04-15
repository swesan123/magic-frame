#!/bin/bash

MODE=$(cat /home/pi/magic-frame/mode.txt 2>/dev/null)

if [ "$MODE" = "stealth" ]; then
    DIR="/home/pi/magic-frame/stealth_media"
else
    DIR="/home/pi/magic-frame/media"
fi

mpv \
--fs \
--loop-playlist=inf \
--shuffle \
--no-audio \
--video-rotate=270 \
--image-display-duration=5 \
--no-osd-bar --osd-level=0 --cursor-autohide=always \
"$DIR"

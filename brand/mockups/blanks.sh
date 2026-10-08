#!/usr/bin/env bash
# Blank product photos for the mockups. The logo is added afterwards by compose.mjs,
# so the photos must carry no print, text or logo of their own.
set -u
cd "$(dirname "$0")"
NB="no logo, no text, no print, no label, photorealistic, high detail"
d() { [ -e raw/$1.jpg ] || [ -e raw/$1.png ] || python3 draw.py --id "$1" --prompt "$2, $NB" || echo "FAILED $1"; }
d tee-white-worn   "Photo of a person wearing a plain blank white crew-neck cotton t-shirt, torso from shoulders to waist, face out of frame, standing against a plain warm grey wall, soft window light, front view"
d hoodie-black     "Studio photo of a plain blank black pullover hoodie on a wooden hanger against a white wall, front view, soft shadows"
d mug-white        "Product photo of a plain white ceramic coffee mug on a light oak table, side view, handle on the right, soft morning light, shallow depth of field"
d mug-black        "Product photo of a plain matte black ceramic coffee mug on a pale stone counter, side view, handle on the right, soft daylight"
d cup-takeaway     "Product photo of a plain white paper takeaway coffee cup with a black plastic lid standing on a wooden cafe counter, front view, soft light, blurred cafe background"
d notebook-black   "Top-down photo of a closed plain black hardcover notebook with an elastic band on a light wooden desk, a pen beside it, soft daylight"
d tote-natural     "Photo of a plain blank natural cotton canvas tote bag hanging flat on a white wall hook, front view, soft daylight"
d cap-black        "Studio product photo of a plain black six-panel baseball cap, three-quarter front view, on a light grey background"
d bottle-white     "Product photo of a plain matte white stainless steel water bottle standing on a wooden table, front view, soft daylight"
d badge-lanyard    "Top-down photo of a blank white name badge card in a clear holder on a black lanyard, lying on a light grey desk"
d banner-foyer     "Photo of a plain blank black vertical pull-up banner standing in a bright modern church foyer with timber and plants, front view"
d tote-black       "Photo of a plain blank black canvas tote bag held by a person against a light concrete wall, front view, face out of frame"

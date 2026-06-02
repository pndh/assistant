import torch
import sounddevice as sd
import sys
import re
import os
import warnings

# --- Silence the PyTorch/Silero logs ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")

# --- The Garbage Collector Function ---
def clean_llm_garbage(raw_text):
    # Trap 1: Find EVERY string of text wrapped in double quotes
    quotes = re.findall(r'"([^"]*)"', raw_text)

    if quotes:
        # Join the separate quoted blocks with an ellipsis to force a TTS pause
        text = ' ... '.join(item.strip() for item in quotes if item.strip())
    else:
        # Trap 2: Chop off everything after a Markdown divider
        text = re.split(r'---|===|\*\*\*', raw_text)[0]
        # Trap 3: Chop off everything after annoying meta-words
        text = re.split(r'\b(Instruction|Note|Explanation):', text, flags=re.IGNORECASE)[0]
        # Trap 4: Nuke any bracketed [SYSTEM] or (Note) tags
        text = re.sub(r'\[.*?\]|\(.*?\)', '', text)

    # Trap 5: Safe-character filter (removes emojis for Silero)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\']', '', text)

    return text.strip()

# 1. Get text from terminal and clean it
raw_input = sys.argv[1] if len(sys.argv) > 1 else "Hello there!"
clean_text = clean_llm_garbage(raw_input)

# Fallback
if not clean_text:
    clean_text = "Hmph."

# 2. Load Silero TTS (Runs entirely on CPU in RAM)
model, _ = torch.hub.load(
    repo_or_dir='snakers4/silero-models',
    model='silero_tts',
    language='en',
    speaker='v3_en'
)

# 3. Generate and Play Audio with Lip-Sync
sample_rate = 48000
flag_file = "/tmp/avatar_speaking"

try:
    audio = model.apply_tts(text=clean_text, speaker='en_21', sample_rate=sample_rate)

    # Create active speaking flag file for avatar.py
    with open(flag_file, 'w') as f:
        f.write("1")

    sd.play(audio.numpy(), sample_rate)
    sd.wait()
except Exception as e:
    pass # Silently fail
finally:
    # Safely clear active speaking flag so avatar returns to idle state
    if os.path.exists(flag_file):
        os.remove(flag_file)

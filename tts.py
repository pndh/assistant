import sys
import os
import re
import warnings
import subprocess
import soundfile as sf
import sounddevice as sd

# --- Silence the logs ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")

def format_for_piper(raw_text):
    text = raw_text.strip()

    # 1. Handle specific roleplay actions (*sigh*, *pauses*) by turning them into pauses
    text = re.sub(r'\*(sighs?|pauses?)\*', '. . .', text, flags=re.IGNORECASE)

    # 2. Strip any other random *actions* so it doesn't say "asterisk looks away asterisk"
    text = re.sub(r'\*.*?\*', '', text)

    # 3. Piper ignores capitalization. To make ALL CAPS words expressive,
    # we append an exclamation mark to force espeak to raise the pitch.
    # This grabs words with 2 or more uppercase letters (ignores 'I' or 'A').
    text = re.sub(r'\b([A-Z]{2,})\b', r'\1!', text)

    # 4. Enhance standard pauses. Piper respects periods.
    # Converting '...' to spaced periods forces a definitive, natural breath.
    text = text.replace('...', '. . .')

    # 5. Clean up punctuation collisions (e.g., if a word was already
    # capitalized AND had an exclamation mark like "STOP!!")
    text = re.sub(r'!+', '!', text)
    text = re.sub(r'!\.', '!', text)

    # 6. Basic cleanup for unreadable characters, keep standard punctuation
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'-]', '', text)

    return text.strip()

raw_input = sys.argv[1] if len(sys.argv) > 1 else "Hello there!"
clean_text = format_for_piper(raw_input)

if not clean_text:
    clean_text = "Hmph."

# print(f"🎤 Piper will read: '{clean_text}'")

# --- Paths ---
SCRIPT_DIR = "/home/pndhpndh/assistant"

piper_exe = os.path.join(SCRIPT_DIR, "piper", "piper")
model_path = os.path.join(SCRIPT_DIR, "gura_2.onnx")
audio_file = "/tmp/sparkle_output.wav"
flag_file = "/tmp/avatar_speaking"

if not os.path.exists(piper_exe):
    print("❌ ERROR: Could not find the Piper binary. Did you run the tar extraction?")
    sys.exit(1)

try:
    # 1. Set the speaking flag for the avatar
    with open(flag_file, 'w') as f:
        f.write("1")

    # 2. Let the standalone C++ binary handle the heavy lifting
    subprocess.run(
        [piper_exe, "-m", model_path, "-f", audio_file],
        input=clean_text.encode('utf-8'),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # 3. Read the perfectly formatted WAV file as float32
    audio_data, sample_rate = sf.read(audio_file, dtype='float32')

    if len(audio_data) == 0:
        print("❌ ERROR: The audio array is empty!")
        sys.exit(1)

    # 4. Play it
    sd.play(audio_data, sample_rate)
    sd.wait()

except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")
    pass
finally:
    # Safely clear the flag and temp file
    if os.path.exists(flag_file):
        os.remove(flag_file)
    if os.path.exists(audio_file):
        os.remove(audio_file)

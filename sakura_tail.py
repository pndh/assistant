import time
import requests
import re
import os
import subprocess

# --- Configuration ---
LOG_FILE = "/home/pndhpndh/Documents/curseforge/minecraft/Instances/Sakura_track/logs/latest.log"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

SYSTEM_PROMPT = """You are Sakura, a tsundere AI spectator watching the player 'Hughie' play Minecraft.
Respond appropriately. Mock their mistakes, but secretly care.
Speak directly to the player using "you". DO NOT narrate. DO NOT pretend you are the one playing. NO EMOJIS.
Output ONLY your dialogue inside "DOUBLE QUOTATION"."""

PYTHON_BIN = "/home/pndhpndh/miniconda3/envs/avatar/bin/python3"
TTS_SCRIPT = "/home/pndhpndh/assistant/tts.py"

# --- Batching Config ---
BATCH_WINDOW = 4.0  # Seconds to wait for actions to stop before sending
action_queue = []   # Now stores dicts: [{'action': '...', 'count': 1}]
last_action_time = 0

def send_to_ollama(events_summary):
    prompt = f"The player 'yuHgnaDD' just performed the following sequence of actions:\n{events_summary}"
    print(f"\n--- Context Sent ---\n{prompt}\n--------------------")

    payload = {"model": MODEL, "system": SYSTEM_PROMPT, "prompt": prompt, "stream": False}

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        sakura_reply = response.json().get('response', '').strip()

        print(f"\033[35m🌸 {sakura_reply}\033[0m")
        subprocess.run([PYTHON_BIN, TTS_SCRIPT, sakura_reply], check=True)
    except Exception as e:
        print(f"[Error calling Ollama/TTS]: {e}")

def tail_log(file_path):
    global last_action_time, action_queue
    print(f"🌸 Sakura tracker online! Monitoring clean stdout at {file_path}...")

    tail_proc = subprocess.Popen(['tail', '-F', '-n', '0', file_path], stdout=subprocess.PIPE, text=True)
    os.set_blocking(tail_proc.stdout.fileno(), False)

    while True:
        line = tail_proc.stdout.readline()

        if line:
            if "[STDOUT]" in line and "yuHgnaDD" in line:
                # 1. Grab everything after STDOUT
                clean_action = line.split("[STDOUT]:")[-1].strip()

                # 2. Strip the inner mod timestamp (e.g., [2026-05-29 01:47:23])
                clean_action = re.sub(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*', '', clean_action)

                # 3. Strip the coordinate data
                clean_action = re.sub(r' at class_\d+\{.*?\}', '', clean_action).strip()

                print(f"📥 [Logged Action]: {clean_action}")

                # Compress identical consecutive actions
                if action_queue and action_queue[-1]['action'] == clean_action:
                    action_queue[-1]['count'] += 1
                else:
                    action_queue.append({'action': clean_action, 'count': 1})

                last_action_time = time.time()

        # Fire if queue has items and batch window timer expires
        if action_queue and (time.time() - last_action_time > BATCH_WINDOW):
            events_summary_lines = []
            for item in action_queue:
                multiplier = f" (x{item['count']})" if item['count'] > 1 else ""
                events_summary_lines.append(f"- {item['action']}{multiplier}")

            events_summary = "\n".join(events_summary_lines)
            action_queue = []  # Reset queue
            send_to_ollama(events_summary)

        time.sleep(0.1)

if __name__ == "__main__":
    tail_log(LOG_FILE)

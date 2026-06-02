import time
import subprocess
import os

# 1. Path to your specific Minecraft instance's log file
# (Adjust "Sakura_Entity" if your folder name is different)
LOG_FILE = os.path.expanduser("/home/pndhpndh/Documents/curseforge/minecraft/Instances/Sakura_Entity/logs/latest.log")

# 2. What name does the mod use in the chat? 
# Usually it's "The Entity", but change it if you renamed her in the config!
AI_NAME = "The Entity"

def process_new_line(line):
    # Check if the line is a chat message AND contains the AI's name
    if "[CHAT]" in line and AI_NAME in line:
        # Split the line to isolate the actual message
        parts = line.split(AI_NAME)
        if len(parts) > 1:
            # Clean up leftover brackets, colons, or spaces
            message = parts[1].strip(" >:]")
            print(f"\n[MC Bridge] Intercepted message: {message}")
            
            # Fire your exact TTS command in the background!
            subprocess.Popen([
                "/home/pndhpndh/miniconda3/envs/avatar/bin/python3",
                "/home/pndhpndh/assistant/tts.py",
                message
            ])

def tail_log():
    if not os.path.exists(LOG_FILE):
        print(f"Error: Could not find log file at {LOG_FILE}")
        print("Make sure Minecraft is running!")
        return

    print(f"👀 Watching Minecraft log for {AI_NAME}...\n")
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        # Jump to the very end of the file so she doesn't read old messages
        f.seek(0, 2) 
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1) # Wait a split second and check again
                continue
            process_new_line(line)

if __name__ == "__main__":
    tail_log()

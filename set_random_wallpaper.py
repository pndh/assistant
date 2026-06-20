import os
import random
import sqlite3
import re
import subprocess
import time

DB_PATH = "/home/pndhpndh/.local/share/waywallen/waywallen-v2.db"
CONFIG_PATH = "/home/pndhpndh/.config/waywallen/config.toml"
DOWNLOADS_DIR = "/home/pndhpndh/Downloads"
APPIMAGE_PATH = "/home/pndhpndh/Downloads/waywallen-0.1.6-x86_64.AppImage"

def get_random_image():
    valid_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
    images = [f for f in os.listdir(DOWNLOADS_DIR) if os.path.splitext(f)[1].lower() in valid_extensions]
    if not images:
        return None
    return random.choice(images)

def register_wallpaper_in_db(image_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure Downloads library exists for image plugin (plugin_id = 2)
    cursor.execute("SELECT id FROM library WHERE path = ?", (DOWNLOADS_DIR,))
    row = cursor.fetchone()
    if row:
        library_id = row[0]
    else:
        cursor.execute("INSERT INTO library (plugin_id, path, metadata) VALUES (?, ?, ?)", (2, DOWNLOADS_DIR, '{}'))
        library_id = cursor.lastrowid

    # Check if item already exists
    cursor.execute("SELECT id FROM item WHERE library_id = ? AND path = ?", (library_id, image_name))
    row = cursor.fetchone()
    if row:
        item_id = row[0]
    else:
        display_name = os.path.splitext(image_name)[0]
        # Insert item with plugin_id=2 (image), type='image'
        now_ms = int(time.time() * 1000)
        cursor.execute(
            "INSERT INTO item (plugin_id, library_id, path, type, display_name, create_at, update_at, sync_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (2, library_id, image_name, 'image', display_name, now_ms, now_ms, now_ms)
        )
        item_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return item_id

def update_config(item_id):
    with open(CONFIG_PATH, 'r') as f:
        content = f.read()

    # Update [global] last_wallpaper
    content = re.sub(r'last_wallpaper\s*=\s*"\d+"', f'last_wallpaper = "{item_id}"', content)
    content = re.sub(r'last_wallpaper\s*=\s*"\w+-\w+-\w+-\w+-\w+"', f'last_wallpaper = "{item_id}"', content) # in case it's uuid
    # Also replace any display section last_wallpaper values
    content = re.sub(r'(last_wallpaper\s*=\s*)"[^"]+"', r'\1' + f'"{item_id}"', content)

    with open(CONFIG_PATH, 'w') as f:
        f.write(content)

def launch_waywallen():
    # Kill any existing waywallen processes first
    subprocess.run(["pkill", "-f", "waywallen"])
    time.sleep(1)
    
    # Launch waywallen AppImage in background
    # We use nohup and redirect output to run cleanly as daemon
    cmd = f"nohup {APPIMAGE_PATH} --no-ui --no-tray > /dev/null 2>&1 &"
    subprocess.Popen(cmd, shell=True)
    print("Launched waywallen daemon.")

if __name__ == '__main__':
    img = get_random_image()
    if not img:
        print("No image found in Downloads.")
        sys.exit(1)
    
    print(f"Selected random image: {img}")
    item_id = register_wallpaper_in_db(img)
    print(f"Registered in DB with ID: {item_id}")
    update_config(item_id)
    print("Updated config.toml.")
    launch_waywallen()
    print("Done!")

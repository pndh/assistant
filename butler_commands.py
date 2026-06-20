import os
import sys
import shutil
import subprocess

def organize_directory(target_dir):
    if not os.path.exists(target_dir):
        print(f"Directory {target_dir} does not exist.")
        return
    
    categories = {
        'Documents': ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.csv', '.pptx', '.epub'],
        'Images': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp'],
        'Videos': ['.mp4', '.mkv', '.avi', '.mov', '.flv'],
        'Archives': ['.zip', '.tar', '.gz', '.bz2', '.xz', '.rar', '.7z'],
        'Code': ['.py', '.js', '.ts', '.html', '.css', '.json', '.sh', '.go', '.rs', '.java', '.cpp', '.c'],
    }

    print(f"Organizing {target_dir}...")
    moved_count = 0

    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        if os.path.isdir(item_path):
            continue
        
        _, ext = os.path.splitext(item.lower())
        target_category = 'Other'
        for cat, extensions in categories.items():
            if ext in extensions:
                target_category = cat
                break
        
        cat_dir = os.path.join(target_dir, target_category)
        os.makedirs(cat_dir, exist_ok=True)
        
        try:
            shutil.move(item_path, os.path.join(cat_dir, item))
            moved_count += 1
        except Exception as e:
            print(f"Could not move {item}: {e}")
            
    print(f"Successfully organized {moved_count} files.")

def get_system_stats():
    stats = []
    
    # 1. Disk usage
    try:
        total, used, free = shutil.disk_usage("/")
        stats.append(f"Disk Usage: {used // (2**30)}GB used of {total // (2**30)}GB ({free // (2**30)}GB free)")
    except Exception as e:
        stats.append(f"Disk Check Failed: {e}")
        
    # 2. Memory usage
    try:
        mem_output = subprocess.check_output("free -h", shell=True).decode('utf-8')
        lines = mem_output.strip().split('\n')
        if len(lines) > 1:
            stats.append(f"Memory: {lines[1].strip()}")
    except Exception:
        pass
        
    # 3. Uptime
    try:
        uptime = subprocess.check_output("uptime -p", shell=True).decode('utf-8').strip()
        stats.append(f"System Uptime: {uptime}")
    except Exception:
        pass

    return "\n".join(stats)

def set_volume(level):
    # Try pactl or amixer to set system volume
    try:
        subprocess.run(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%", shell=True, check=True)
        print(f"Volume set to {level}%")
        return True
    except Exception:
        try:
            subprocess.run(f"amixer set Master {level}%", shell=True, check=True)
            print(f"Volume set to {level}%")
            return True
        except Exception as e:
            print(f"Failed to adjust volume: {e}")
            return False

def save_session_state():
    try:
        import json
        import glob
        
        # 1. KDE-level fallback save session
        try:
            subprocess.run(["kwriteconfig6", "--file", "ksmserverrc", "--group", "General", "--key", "loginMode", "restoreSavedSession"], check=True)
            subprocess.run([
                "dbus-send", "--dest=org.kde.ksmserver", "/KSMServer", "org.kde.KSMServerInterface.saveCurrentSession"
            ], check=True)
        except Exception:
            pass
            
        # 2. Extract active user processes & terminal directories
        uid = os.getuid()
        apps = set()
        shell_dirs = set()
        
        for path in glob.glob('/proc/[0-9]*'):
            try:
                with open(os.path.join(path, 'status'), 'r') as f:
                    content = f.read()
                uid_line = [line for line in content.split('\n') if line.startswith('Uid:')][0]
                proc_uid = int(uid_line.split()[1])
                if proc_uid != uid:
                    continue
                    
                with open(os.path.join(path, 'comm'), 'r') as f:
                    comm = f.read().strip()
                
                if 'firefox' in comm:
                    apps.add('firefox')
                elif 'chrome' in comm or 'chromium' in comm:
                    apps.add('chrome')
                elif 'spotify' in comm:
                    apps.add('spotify')
                elif 'antigravity-ide' in comm or 'code' in comm:
                    apps.add('code')
                elif comm in ['zsh', 'bash']:
                    cwd = os.readlink(os.path.join(path, 'cwd'))
                    if os.path.exists(cwd):
                        shell_dirs.add(cwd)
            except Exception:
                continue

        state_data = {
            "apps": list(apps),
            "shell_dirs": list(shell_dirs),
            "restored": False
        }
        
        state_file = "/home/pndhpndh/assistant/saved_session_state.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)
            
        print("Session state saved successfully.")
        return True
    except Exception as e:
        print(f"Failed to save session state: {e}")
        return False

def load_session_state():
    try:
        import json
        import glob
        state_file = "/home/pndhpndh/assistant/saved_session_state.json"
        if not os.path.exists(state_file):
            print("No saved state found.")
            return False
            
        with open(state_file, "r") as f:
            state_data = json.load(f)
            
        apps = state_data.get("apps", [])
        shell_dirs = state_data.get("shell_dirs", [])
        
        # Determine already running apps
        running = set()
        uid = os.getuid()
        for path in glob.glob('/proc/[0-9]*'):
            try:
                with open(os.path.join(path, 'status'), 'r') as f:
                    status = f.read()
                uid_line = [line for line in status.split('\n') if line.startswith('Uid:')][0]
                if int(uid_line.split()[1]) == uid:
                    with open(os.path.join(path, 'comm'), 'r') as f:
                        comm = f.read().strip()
                    if 'firefox' in comm: running.add('firefox')
                    elif 'chrome' in comm or 'chromium' in comm: running.add('chrome')
                    elif 'spotify' in comm: running.add('spotify')
                    elif 'antigravity-ide' in comm or 'code' in comm: running.add('code')
            except Exception:
                continue

        # Restore applications
        if "firefox" in apps and "firefox" not in running:
            subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if "chrome" in apps and "chrome" not in running:
            subprocess.Popen(["google-chrome-stable"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if "spotify" in apps and "spotify" not in running:
            subprocess.Popen(["spotify"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if "code" in apps and "code" not in running:
            subprocess.Popen(["antigravity-ide"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        # Restore terminals in Konsole
        for directory in shell_dirs:
            subprocess.Popen(["konsole", "--workdir", directory], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        state_data["restored"] = True
        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)
            
        print("Session state loaded successfully.")
        return True
    except Exception as e:
        print(f"Failed to load session state: {e}")
        return False

def skip_track(target_type=None):
    try:
        import re
        cmd = ["dbus-send", "--dest=org.freedesktop.DBus", "--print-reply", "/org/freedesktop/DBus", "org.freedesktop.DBus.ListNames"]
        res = subprocess.check_output(cmd).decode('utf-8')
        players = re.findall(r'"(org\.mpris\.MediaPlayer2\.[^"]+)"', res)
        
        target_players = []
        for player in players:
            player_lower = player.lower()
            if target_type == 'spotify':
                if 'spotify' in player_lower:
                    target_players.append(player)
            elif target_type in ['youtube', 'yt', 'ytmusic', 'youtubemusic']:
                if any(b in player_lower for b in ['firefox', 'chrome', 'chromium', 'opera', 'brave', 'vivaldi']):
                    target_players.append(player)
            else:
                target_players.append(player)
                
        if not target_players:
            # Fallback to all players if target filter yielded nothing
            target_players = players
            
        success = False
        for player in target_players:
            try:
                subprocess.run([
                    "dbus-send", "--print-reply", f"--dest={player}",
                    "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.Next"
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                success = True
                print(f"Skipped track on: {player}")
            except Exception:
                pass
        return success
    except Exception as e:
        print(f"Failed to skip track: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python butler_commands.py [organize <path> | stats | volume <level> | savestate | loadstate | next [spotify|youtube]]")
        sys.exit(0)
        
    cmd = sys.argv[1].lower()
    if cmd == 'organize':
        path = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/Downloads")
        organize_directory(path)
    elif cmd == 'stats':
        print(get_system_stats())
    elif cmd == 'volume':
        level = sys.argv[2] if len(sys.argv) > 2 else "50"
        set_volume(level)
    elif cmd == 'savestate':
        save_session_state()
    elif cmd == 'loadstate':
        load_session_state()
    elif cmd == 'next':
        player_type = sys.argv[2].lower() if len(sys.argv) > 2 else None
        skip_track(player_type)
    else:
        print(f"Unknown command: {cmd}")



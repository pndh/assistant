import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import json
import os
import re
import threading
import subprocess
import requests

HISTORY_PATH = "/home/pndhpndh/assistant/chat_history.json"
BRIDGE_PATH = "/home/pndhpndh/assistant/chat_bridge.json"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
DEFAULT_GEMINI_KEY = "AIzaSyCbXTN6VXVG6OVAof90_YgpBcL_dWv3ZfY"
MODEL = "gemini-3.1-flash-lite"

SYSTEM_PROMPT = """You are Sakura, a caring but tsundere AI assistant and personal butler for Hughie.
Respond appropriately and tightly in a maximum of 20 words. Speak directly to him using "you". Strictly DO NOT use the word "baka". Maintain your tsundere attitude.
NO EMOJIS. Output only your dialogue."""

def get_gemini_key():
    # Attempt to read from .zshrc dynamically
    zshrc_path = "/home/pndhpndh/.zshrc"
    if os.path.exists(zshrc_path):
        try:
            with open(zshrc_path, "r") as f:
                content = f.read()
            match = re.search(r'GEMINI_API_KEY="([^"]+)"', content)
            if match:
                return match.group(1)
        except Exception:
            pass
    return DEFAULT_GEMINI_KEY

class SakuraChatWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Sakura Chat")
        GLib.set_prgname("sakura-chat")
        
        icon_path = "/home/pndhpndh/assistant/closed_kei.png"
        if os.path.exists(icon_path):
            try:
                self.set_icon_from_file(icon_path)
            except Exception as e:
                print(f"Error setting window icon: {e}")

        self.set_default_size(450, 600)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.apply_css()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        self.add(vbox)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        vbox.pack_start(scrolled, True, True, 0)

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.get_style_context().add_class("chat-view")
        scrolled.add(self.text_view)

        self.text_buffer = self.text_view.get_buffer()
        self.create_tags()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(hbox, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Type a message, butler command, or /agent <task>...")
        self.entry.connect("activate", self.on_send_clicked)
        hbox.pack_start(self.entry, True, True, 0)

        send_btn = Gtk.Button(label="Send")
        send_btn.connect("clicked", self.on_send_clicked)
        hbox.pack_start(send_btn, False, False, 0)

        self.history = []
        self.load_history()
        
        # Check and auto-restore state on startup
        threading.Thread(target=self.auto_restore_state_bg, daemon=True).start()
        
        self.agent_mode_active = False
        GLib.timeout_add(1000, self.poll_bridge)

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css = b"""
        window {
            background-color: #1e1e2e;
        }
        .chat-view {
            background-color: #181825;
            color: #cdd6f4;
            font-family: sans-serif;
            font-size: 14px;
            padding: 10px;
        }
        entry {
            background-color: #313244;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 8px;
        }
        entry:focus {
            border-color: #cba6f7;
        }
        button {
            background-color: #cba6f7;
            color: #11111b;
            font-weight: bold;
            border-radius: 6px;
            padding: 8px 16px;
        }
        button:hover {
            background-color: #f5c2e7;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def create_tags(self):
        self.user_tag = self.text_buffer.create_tag("user_tag", weight=700, foreground="#89b4fa")
        self.sakura_tag = self.text_buffer.create_tag("sakura_tag", weight=700, foreground="#f5c2e7")
        self.system_tag = self.text_buffer.create_tag("system_tag", style=2, foreground="#a6adc8")

    def append_message(self, sender, text, save=True):
        end_iter = self.text_buffer.get_end_iter()
        if sender == "You":
            self.text_buffer.insert_with_tags(end_iter, f"{sender}: ", self.user_tag)
        elif sender == "Sakura":
            self.text_buffer.insert_with_tags(end_iter, f"{sender}: ", self.sakura_tag)
        else:
            self.text_buffer.insert_with_tags(end_iter, f"{sender}: ", self.system_tag)
            
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, f"{text}\n\n")
        
        mark = self.text_buffer.get_insert()
        self.text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

        if save:
            self.history.append({"sender": sender, "text": text})
            self.save_history()

    def load_history(self):
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, "r") as f:
                    self.history = json.load(f)
                for msg in self.history:
                    self.append_message(msg["sender"], msg["text"], save=False)
            except Exception as e:
                print(f"Error loading history: {e}")
        
        if not self.history:
            self.append_message("Sakura", "Hmph. What do you want now? I'm finally back online.")

    def save_history(self):
        try:
            with open(HISTORY_PATH, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def auto_restore_state_bg(self):
        state_file = "/home/pndhpndh/assistant/saved_session_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                if not data.get("restored", True):
                    GLib.idle_add(self.append_message, "System", "Auto-restoring saved session state...")
                    subprocess.run(["python3", "/home/pndhpndh/assistant/butler_commands.py", "loadstate"], check=True)
                    reply = self.get_sakura_reply("load state", command_info="You successfully auto-restored their session state on system startup. Welcome them back in your tsundere persona.")
                    GLib.idle_add(self.append_message, "Sakura", reply)
                    self.speak_bg(reply)
            except Exception as e:
                print(f"Auto-restore failed: {e}")

    def remove_last_system_message(self):
        if self.history and self.history[-1]["sender"] == "System":
            self.history.pop()
            self.save_history()
        GLib.idle_add(self.rebuild_buffer)

    def rebuild_buffer(self):
        self.text_buffer.set_text("")
        for msg in self.history:
            sender = msg["sender"]
            text = msg["text"]
            end_iter = self.text_buffer.get_end_iter()
            if sender == "You":
                self.text_buffer.insert_with_tags(end_iter, f"{sender}: ", self.user_tag)
            elif sender == "Sakura":
                self.text_buffer.insert_with_tags(end_iter, f"{sender}: ", self.sakura_tag)
            else:
                self.text_buffer.insert_with_tags(end_iter, f"{sender}: ", self.system_tag)
            end_iter = self.text_buffer.get_end_iter()
            self.text_buffer.insert(end_iter, f"{text}\n\n")
    def get_sakura_reply(self, text, command_info=None):
        # Filter history to only include dialogue and limit to the last 5 messages
        dialogue_history = [msg for msg in self.history[:-1] if msg["sender"] in ["You", "Sakura"]]
        recent_history = dialogue_history[-5:]
        
        sys_prompt = SYSTEM_PROMPT
        if command_info:
            sys_prompt += f"\n\nContext: {command_info}"
            
        messages = [{"role": "system", "content": sys_prompt}]
        for msg in recent_history:
            if msg["sender"] == "You":
                messages.append({"role": "user", "content": msg["text"]})
            elif msg["sender"] == "Sakura":
                messages.append({"role": "assistant", "content": msg["text"]})
        
        messages.append({"role": "user", "content": text})
        
        key = get_gemini_key()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }
        payload = {
            "model": MODEL,
            "messages": messages,
        }
        try:
            res = requests.post(GEMINI_ENDPOINT, json=payload, headers=headers, timeout=20)
            res.raise_for_status()
            return res.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        except Exception as e:
            return f"I tried to respond, but I couldn't reach the backend: {e}"

    def on_send_clicked(self, widget):
        text = self.entry.get_text().strip()
        if not text:
            return
        
        self.entry.set_text("")
        self.append_message("You", text)
        
        threading.Thread(target=self.handle_input_bg, args=(text,), daemon=True).start()

    def handle_input_bg(self, text):
        cleaned_text = text.lower()
        
        # 0. Check for /agent command
        if text.startswith("/agent "):
            agent_instruction = text[7:].strip()
            GLib.idle_add(self.append_message, "System", "Forwarded command to Antigravity IDE agent. Waiting for agent turn...")
            
            data = {
                "user_message": agent_instruction,
                "agent_response": "",
                "status": "pending_agent"
            }
            with open(BRIDGE_PATH, "w") as f:
                json.dump(data, f, indent=2)
                
            self.agent_mode_active = True
            return

        # 1. Detect butler system commands
        if "system check" in cleaned_text or "system stats" in cleaned_text or "/stats" in cleaned_text or "disk usage" in cleaned_text:
            GLib.idle_add(self.append_message, "System", "Running system check...")
            try:
                res = subprocess.check_output(["python3", "/home/pndhpndh/assistant/butler_commands.py", "stats"]).decode('utf-8').strip()
                reply = self.get_sakura_reply(text, command_info=f"You successfully ran a system check. The report is:\n{res}\nProvide a brief tsundere summary of this.")
            except Exception as e:
                reply = f"Hmph! I couldn't even check the system stats: {e}"
            self.remove_last_system_message()
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)
            
        elif "organize downloads" in cleaned_text or "/organize" in cleaned_text:
            GLib.idle_add(self.append_message, "System", "Organizing downloads...")
            try:
                res = subprocess.check_output(["python3", "/home/pndhpndh/assistant/butler_commands.py", "organize"]).decode('utf-8').strip()
                reply = self.get_sakura_reply(text, command_info=f"You successfully organized their Downloads folder. Result: {res}. Tell them it's clean now.")
            except Exception as e:
                reply = f"Hmph! Your downloads are too messy to clean up: {e}"
            self.remove_last_system_message()
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)
            
        elif "set volume" in cleaned_text or "volume" in cleaned_text or "/volume" in cleaned_text:
            import re
            match = re.search(r'\d+', cleaned_text)
            level = match.group(0) if match else "50"
            GLib.idle_add(self.append_message, "System", f"Setting volume to {level}%...")
            try:
                subprocess.run(["python3", "/home/pndhpndh/assistant/butler_commands.py", "volume", level], check=True)
                reply = self.get_sakura_reply(text, command_info=f"You set the volume to {level}%. Warn them not to damage their ears.")
            except Exception as e:
                reply = f"I couldn't adjust the volume: {e}"
            self.remove_last_system_message()
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)
            
        elif "spotify" in cleaned_text or "playlist" in cleaned_text:
            GLib.idle_add(self.append_message, "System", "Fetching a random track from your Spotify playlist...")
            try:
                import random
                import re
                res = requests.get("https://open.spotify.com/playlist/09cQBZJSadYguo5OxyAszc", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                tracks = list(set(re.findall(r"spotify:track:([a-zA-Z0-9]+)", res.text)))
                if tracks:
                    track_id = random.choice(tracks)
                    url = f"https://open.spotify.com/track/{track_id}?autoplay=true"
                    subprocess.run(["xdg-open", url])
                    self.remove_last_system_message()
                    reply = self.get_sakura_reply(text, command_info="You successfully opened a random Spotify track for them. Acknowledge this.")
                    GLib.idle_add(self.append_message, "Sakura", reply)
                    self.speak_bg(reply)
                else:
                    raise ValueError("No tracks found in the HTML.")
            except Exception as e:
                self.remove_last_system_message()
                GLib.idle_add(self.append_message, "System", f"Failed to load Spotify playlist: {e}")

        elif "youtube music" in cleaned_text or "yt music" in cleaned_text or "recap" in cleaned_text:
            GLib.idle_add(self.append_message, "System", "Selecting a random song from your YouTube Music playlist...")
            try:
                import random
                cmd = ["yt-dlp", "--cookies-from-browser", "firefox", "--get-id", "--flat-playlist", "https://music.youtube.com/playlist?list=RDTMAK5uy_nilrsVWxrKskY0ZUpVZ3zpB0u4LwWTVJ4"]
                res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
                ids = [line.strip() for line in res.split('\n') if line.strip()]
                if ids:
                    video_id = random.choice(ids)
                    url = f"https://music.youtube.com/watch?v={video_id}&list=RDTMAK5uy_nilrsVWxrKskY0ZUpVZ3zpB0u4LwWTVJ4"
                else:
                    url = "https://music.youtube.com/watch?list=RDTMAK5uy_nilrsVWxrKskY0ZUpVZ3zpB0u4LwWTVJ4"
            except Exception:
                url = "https://music.youtube.com/watch?list=RDTMAK5uy_nilrsVWxrKskY0ZUpVZ3zpB0u4LwWTVJ4"
            
            subprocess.run(["xdg-open", url])
            self.remove_last_system_message()
            reply = self.get_sakura_reply(text, command_info="You selected a random track from their recap playlist on YouTube Music and opened it. Acknowledge this.")
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)

        elif "save state" in cleaned_text or "save session" in cleaned_text or "/save" in cleaned_text:
            GLib.idle_add(self.append_message, "System", "Saving current session state...")
            try:
                subprocess.run(["python3", "/home/pndhpndh/assistant/butler_commands.py", "savestate"], check=True)
                reply = self.get_sakura_reply(text, command_info="You successfully saved their session state. Tell them they can go boot Windows to play games now and you'll restore everything when they log back in.")
            except Exception as e:
                reply = f"I tried to save your state, but something went wrong: {e}"
            self.remove_last_system_message()
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)

        elif "load state" in cleaned_text or "load session" in cleaned_text or "/load" in cleaned_text:
            GLib.idle_add(self.append_message, "System", "Restoring session state...")
            try:
                subprocess.run(["python3", "/home/pndhpndh/assistant/butler_commands.py", "loadstate"], check=True)
                reply = self.get_sakura_reply(text, command_info="You successfully restored their session state. Welcome them back.")
            except Exception as e:
                reply = f"I tried to load your state, but something went wrong: {e}"
            self.remove_last_system_message()
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)

        elif "next" in cleaned_text or "/next" in cleaned_text:
            player_arg = ""
            if "spotify" in cleaned_text:
                player_arg = "spotify"
            elif "youtube" in cleaned_text or "yt" in cleaned_text:
                player_arg = "youtube"
            
            GLib.idle_add(self.append_message, "System", "Skipping to the next track...")
            try:
                if player_arg:
                    subprocess.run(["python3", "/home/pndhpndh/assistant/butler_commands.py", "next", player_arg], check=True)
                else:
                    subprocess.run(["python3", "/home/pndhpndh/assistant/butler_commands.py", "next"], check=True)
                reply = self.get_sakura_reply(text, command_info=f"You successfully skipped the track on {player_arg or 'the active media player'}. Acknowledge this.")
            except Exception as e:
                reply = f"I tried to skip the track, but something went wrong: {e}"
            self.remove_last_system_message()
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)

        elif "youtube" in cleaned_text or "video" in cleaned_text or "play" in cleaned_text:
            import random
            import urllib.parse
            GLib.idle_add(self.append_message, "System", "Searching Hatsune Miku song on YouTube...")
            songs = [
                "World is Mine",
                "Senbonzakura",
                "Melt",
                "PoPiPo",
                "Romeo and Cinderella",
                "Tell Your World"
            ]
            song = random.choice(songs)
            query = f"Hatsune Miku {song}"
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            subprocess.run(["xdg-open", url])
            self.remove_last_system_message()
            reply = self.get_sakura_reply(text, command_info=f"You searched YouTube for the song '{song}' and opened the page. Acknowledge this.")
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)
            
        else:
            # 2. General conversation -> Gemini API endpoint with History
            GLib.idle_add(self.append_message, "System", "Sakura is thinking...")
            reply = self.get_sakura_reply(text)
            self.remove_last_system_message()
            GLib.idle_add(self.append_message, "Sakura", reply)
            self.speak_bg(reply)


    def poll_bridge(self):
        if not self.agent_mode_active or not os.path.exists(BRIDGE_PATH):
            return True
            
        try:
            with open(BRIDGE_PATH, "r") as f:
                data = json.load(f)
                
            if data.get("status") == "pending_user" and data.get("agent_response"):
                reply = data["agent_response"]
                GLib.idle_add(self.append_message, "Sakura", reply)
                
                data["agent_response"] = ""
                with open(BRIDGE_PATH, "w") as f:
                    json.dump(data, f, indent=2)
                
                self.agent_mode_active = False
                threading.Thread(target=self.speak_bg, args=(reply,), daemon=True).start()
        except Exception as e:
            print(f"Error reading bridge file: {e}")
            
        return True

    def speak_bg(self, text):
        python_bin = "/home/pndhpndh/miniconda3/envs/avatar/bin/python3"
        tts_script = "/home/pndhpndh/assistant/tts.py"
        subprocess.run([python_bin, tts_script, text])

if __name__ == "__main__":
    win = SakuraChatWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

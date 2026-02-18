import psutil
import os
import subprocess
import asyncio
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Container, Vertical
from textual.widgets import Static, Label, Input, Button
from textual.binding import Binding
from textual.events import MouseDown, MouseMove, MouseUp, Key

# --- ASET SUCI: MODULE JAM BLOK ---
DIGITS = {
    "0": ["███", "█ █", "█ █", "█ █", "███"], "1": ["  █", "  █", "  █", "  █", "  █"],
    "2": ["███", "  █", "███", "█  ", "███"], "3": ["███", "  █", "███", "  █", "███"],
    "4": ["█ █", "█ █", "███", "  █", "  █"], "5": ["███", "█  ", "███", "  █", "███"],
    "6": ["███", "█  ", "███", "█ █", "███"], "7": ["███", "  █", "  █", "  █", "  █"],
    "8": ["███", "█ █", "███", "█ █", "███"], "9": ["███", "█ █", "███", "  █", "███"],
    ":": ["   ", " █ ", "   ", " █ ", "   "],
}

def get_ascii_clock(time_str):
    lines = ["", "", "", "", ""]
    for char in time_str:
        digit_lines = DIGITS.get(char, ["   "] * 5)
        for i in range(5): lines[i] += digit_lines[i] + "  "
    return "\n".join(lines)

# --- FITUR: BRIVOL TUI ---
class BrivolMenu(Vertical):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.can_focus = True
        self.bri, self.vol = 100, 85
        self.focus_target = "bri"

    def compose(self) -> ComposeResult:
        yield Label("[bold white]      BRIVOL - TOSS [/]", id="brivol-title")
        with Horizontal(id="brivol-bars"):
            with Vertical(classes="brivol-col", id="col-bri"):
                yield Label("BRIGHT", classes="col-label")
                yield Static("", id="bar-bri", classes="brivol-bar")
                yield Label("100%", id="bri-val", classes="val-label")
            with Vertical(classes="brivol-col", id="col-vol"):
                yield Label("VOLUME", classes="col-label")
                yield Static("", id="bar-vol", classes="brivol-bar")
                yield Label("85%", id="vol-val", classes="val-label")
        yield Label("[UP/DOWN: ADJ] [TAB: SWITCH]", id="brivol-hint")

    def update_bars(self) -> None:
        def make_bar(val):
            levels = val // 20
            return "\n".join(["||" if i <= levels else ".." for i in range(5, 0, -1)])
        self.query_one("#bar-bri").update(make_bar(self.bri))
        self.query_one("#bar-vol").update(make_bar(self.vol))
        self.query_one("#bri-val").update(f"{self.bri}%")
        self.query_one("#vol-val").update(f"{self.vol}%")
        self.query_one("#col-bri").styles.opacity = 1.0 if self.focus_target == "bri" else 0.4
        self.query_one("#col-vol").styles.opacity = 1.0 if self.focus_target == "vol" else 0.4

    def on_key(self, event: Key) -> None:
        if event.key == "tab":
            self.focus_target = "vol" if self.focus_target == "bri" else "bri"
        elif event.key in ("up", "down"):
            diff = 5 if event.key == "up" else -5
            if self.focus_target == "bri":
                self.bri = max(0, min(100, self.bri + diff))
                os.system(f"brightnessctl set {self.bri}% > /dev/null 2>&1")
            else:
                self.vol = max(0, min(100, self.vol + diff))
                os.system(f"amixer set Master {self.vol}% > /dev/null 2>&1")
        elif event.key == "escape":
            self.app.action_hide_all()
        self.update_bars()

# --- ASET SUCI: DRAG & WINDOW LOGIC ---
class FloatingTerminal(Vertical):
    def __init__(self, ws_owner, **kwargs):
        super().__init__(**kwargs)
        self.ws_owner = ws_owner
        self.dragging = False

    def compose(self) -> ComposeResult:
        yield Label("  TOSSMINAL", id="term-header")
        with Horizontal(id="input-area"):
            yield Label("toss#nixos $ ", id="prompt-label")
            yield Input(id="term-input", placeholder="")
        yield Static("Welcome to TOSS. Everything is CLI.\n", id="term-log")

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.y == 0 and self.app.is_floating: 
            self.dragging = True
            self.capture_mouse()
            self.mouse_x, self.mouse_y = event.screen_x, event.screen_y
            self.orig_x = self.styles.offset.x.value
            self.orig_y = self.styles.offset.y.value
        self.query_one("#term-input").focus()

    def on_mouse_move(self, event: MouseMove) -> None:
        if self.dragging:
            dx = event.screen_x - self.mouse_x
            dy = event.screen_y - self.mouse_y
            self.styles.offset = (self.orig_x + dx, self.orig_y + dy)

    def on_mouse_up(self, event: MouseUp) -> None:
        self.dragging = False
        self.release_mouse()

class TOSS(App):
    CSS = """
    Screen { background: #000000; layers: base windows top overlay; overflow: hidden; padding: 0; margin: 0; }
    #main-frame { width: 100%; height: 1fr; border: heavy #a6e22e; background: #000000; margin: 0; padding: 0; }
    #desktop { width: 100%; height: 100%; background: #000000; layer: base; }
    #lock-screen { display: none; width: 100%; height: 100%; background: #000000 98%; layer: overlay; }
    #lock-screen.show { display: block; }
    #lock-container { width: 100%; height: 100%; align: center middle; }
    #big-clock { text-align: center; color: #a6e22e; margin-bottom: 2; width: 100%; }
    #unlock-label { text-align: center; color: #555555; width: 100%; }
    #taskbar { dock: bottom; height: 1; width: 100%; background: #1c1c1c; color: #ffffff; layer: top; }
    .ws-active { background: #a6e22e; color: #000000; text-style: bold; padding: 0 2; }
    .ws-inactive { padding: 0 2; color: #585858; background: #1c1c1c; }
    #spacer { width: 1fr; }
    #stats-area { color: #ffffff; background: #333333; padding: 0 1; }
    #clock { background: #1c1c1c; color: #ffffff; text-style: bold; padding: 0 1; }

    #notify-box { 
        display: none; width: 32; height: auto; background: #111111; border: double #a6e22e; 
        color: #ffffff; layer: overlay; padding: 1; position: absolute;
    }
    #notify-box.show { display: block; }

    #wallpaper-menu, #start-menu, #brivol-menu { display: none; width: 34; height: auto; background: #111111; border: heavy white; layer: overlay; padding: 1; position: absolute; offset-x: 2; offset-y: 1; }
    #wallpaper-menu.show, #start-menu.show, #brivol-menu.show { display: block; }
    #brivol-bars { height: 10; margin: 1 0; align: center middle; }
    .brivol-col { width: 14; align: center middle; text-align: center; }
    .col-label { text-style: bold; color: #888888; margin-bottom: 1; }
    .val-label { color: #ffffff; margin-top: 1; }
    .brivol-bar { color: #a6e22e; text-align: center; height: 5; width: 100%; }
    #brivol-hint { color: #555555; text-align: center; margin-top: 1; }
    .wall-btn, .menu-btn { width: 100%; margin: 0; border: none; background: #1a1a1a; color: #585858; }
    .wall-btn:hover, .menu-btn:hover { background: #a6e22e; color: black; }
    .floating-win { width: 80; height: 24; border: heavy #555555; background: #0c0c0c; layer: windows; position: absolute; }
    .tiling-win { border: solid #333333; background: #000000; layer: windows; position: absolute; margin: 0; padding: 0; }
    #term-header { background: #a6e22e; color: #000000; width: 100%; text-style: bold; height: 1; }
    #term-log { height: 1fr; padding: 0 1; color: #ffffff; overflow-y: scroll; }
    #input-area { height: 1; width: 100%; background: #1a1a1a; padding: 0 1; }
    #prompt-label { color: #a6e22e; text-style: bold; width: auto; }
    #term-input { width: 1fr; height: 1; background: transparent; border: none; color: #ffffff; padding: 0; }
    .hidden { display: none; }
    """

    BINDINGS = [
        Binding("alt+t", "open_terminal", "Terminal"),
        Binding("alt+e", "open_tfiler", "File Explorer"),
        Binding("alt+space", "toggle_float", "Float"),
        Binding("alt+q", "close_active_window", "Close Window"), 
        Binding("alt+1", "switch_ws(1)", "WS 1"),
        Binding("alt+2", "switch_ws(2)", "WS 2"),
        Binding("alt+shift+q", "toggle_menu", "System Menu"),
        Binding("alt+w", "toggle_wallpaper", "Wallpaper"),
        Binding("alt+l", "lock_screen", "Lock"),
        Binding("escape", "hide_all", "Hide"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="main-frame"):
            with Container(id="desktop"):
                yield Container(id="ws-1")
                yield Container(id="ws-2", classes="hidden")
                with Vertical(id="wallpaper-menu"):
                    yield Label("[bold white] SELECT COLOR [/]")
                    yield Button("TOKYO NIGHT", id="wall-grey", classes="wall-btn")
                    yield Button("BLACK DEEP", id="wall-black", classes="wall-btn")
                with Vertical(id="start-menu"):
                    yield Label("[bold white] TOSS SYSTEM [/]")
                    yield Button("WIFI MANAGER", id="btn-wifi", classes="menu-btn")
                    yield Button("BRIVOL CONTROL", id="btn-brivol", classes="menu-btn")
                    yield Button("LOCK SCREEN", id="btn-lock", classes="menu-btn")
                    yield Button("QUIT TOSS", id="btn-quit", classes="menu-btn")
                yield BrivolMenu(id="brivol-menu")
                yield Static("", id="notify-box") 
        with Vertical(id="lock-screen"):
            with Vertical(id="lock-container"):
                yield Static("", id="big-clock") 
                yield Label("SPACE TO UNLOCK", id="unlock-label")
        with Horizontal(id="taskbar"):
            yield Label(" [1] ", id="btn-ws1", classes="ws-active")
            yield Label(" [2] ", id="btn-ws2", classes="ws-inactive")
            yield Static(id="spacer")
            yield Label("...", id="stats-area")
            yield Label("00:00", id="clock")

    def on_mount(self) -> None:
        self.current_ws, self.is_locked, self.is_floating = 1, False, False
        self.last_wifi_status = self.check_wifi_status()
        self.set_interval(1, self.update_system_info)
        self.set_interval(5, self.monitor_network)
        self.action_open_terminal(auto_tfetch=True)

    # --- FITUR NOTIFIKASI ---
    def post_notification(self, message: str, duration: int = 3):
        box = self.query_one("#notify-box")
        screen_w = self.query_one("#desktop").content_size.width
        # Offset-y: 1 biar lebih ke atas mendekati border
        box.styles.offset = (screen_w - 35, 1) 
        box.update(f"[bold #a6e22e]TOSS NOTIFY[/]\n{message}")
        box.add_class("show")
        def hide_notif(): box.remove_class("show")
        asyncio.get_event_loop().call_later(duration, hide_notif)

    def check_wifi_status(self):
        try:
            res = subprocess.getoutput("nmcli -t -f DEVICE,STATE dev | grep connected | wc -l")
            return int(res.strip()) > 0
        except: return False

    def monitor_network(self):
        current = self.check_wifi_status()
        if current != self.last_wifi_status:
            msg = "✔ WiFi Connected" if current else "✘ WiFi Disconnected"
            self.post_notification(msg)
            self.last_wifi_status = current

    # --- LOGIKA KELUAR & WIFI MANAGER ---
    def action_open_wifi_manager(self) -> None:
        if self.is_locked: return
        with self.suspend():
            try:
                os.system("clear")
                print("┌────────────────────────────────────────────────────────┐")
                print("│             TOSS SMART WIFI - INTERFACE SELECT         │")
                print("│        (Press Ctrl+C or Enter empty to EXIT)           │")
                print("├────────────────────────────────────────────────────────┤")
                
                interfaces = subprocess.getoutput("ip -br link show | awk '{print $1}'").split()
                print("  Available Interfaces:")
                for i, net in enumerate(interfaces):
                    desc = "(Wireless)" if net.startswith('w') else "(Wired/Other)"
                    print(f"  [{i}] {net} {desc}")
                
                idx_input = input("\n  Which interface? (number): ").strip()
                if not idx_input: return 

                iface = interfaces[int(idx_input)]
                print(f"\n  Scanning on {iface}...")
                os.system(f"ip link set {iface} up > /dev/null 2>&1")
                os.system(f"nmcli device wifi rescan > /dev/null 2>&1")
                os.system(f"nmcli -f SSID,SIGNAL,BARS,SECURITY device wifi list ifname {iface}")
                
                print("\n  [1] Quick Connect")
                print("  [2] Cancel/Exit")
                
                pilih = input("\n  Option: ").strip()
                if pilih != "1": return 

                ssid = input("  Enter SSID: ").strip()
                if not ssid: return
                pw = input("  Enter Password: ").strip()
                
                print(f"\n  Connecting to {ssid}...")
                cmd = f"nmcli device wifi connect '{ssid}' password '{pw}' ifname {iface}"
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if "Error" in res.stderr:
                    print("  [!] Standard failed. Applying Deep Connect...")
                    os.system(f"nmcli connection delete '{ssid}' > /dev/null 2>&1")
                    deep_cmd = f"nmcli connection add type wifi con-name '{ssid}' ifname {iface} ssid '{ssid}' -- wifi-sec.key-mgmt wpa-psk && nmcli connection modify '{ssid}' wifi-sec.psk '{pw}' && nmcli connection up '{ssid}'"
                    os.system(deep_cmd)
                else:
                    print("  [+] Connected!")
                input("\n  Press Enter to return...")
            except (KeyboardInterrupt, EOFError, ValueError):
                pass 
        self.post_notification("Welcome Back, Bre!")
        self.refresh()
        self.retile_dwm()

    def update_system_info(self) -> None:
        now = datetime.now()
        time_short = now.strftime("%H:%M")
        try:
            self.query_one("#stats-area").update(f"CPU {psutil.cpu_percent()}% | RAM {psutil.virtual_memory().percent}%")
            self.query_one("#clock").update(time_short)
            if self.is_locked: self.query_one("#big-clock").update(get_ascii_clock(time_short))
        except: pass

    def retile_dwm(self):
        ws = self.query_one(f"#ws-{self.current_ws}")
        windows = [w for w in ws.children if isinstance(w, FloatingTerminal)]
        if not windows: return
        screen_w = self.query_one("#desktop").content_size.width
        screen_h = self.query_one("#desktop").content_size.height
        if self.is_floating:
            for win in windows:
                win.styles.width, win.styles.height = 80, 24
                win.styles.offset = ((screen_w - 80) // 2, (screen_h - 24) // 2)
        else:
            count = len(windows)
            if count == 1:
                windows[0].styles.width, windows[0].styles.height = screen_w, screen_h
                windows[0].styles.offset = (0, 0)
            else:
                master_w = int(screen_w * 0.6)
                stack_w, stack_h = screen_w - master_w, screen_h // (count - 1)
                windows[0].styles.width, windows[0].styles.height = master_w, screen_h
                windows[0].styles.offset = (0, 0)
                for i, win in enumerate(windows[1:]):
                    win.styles.width, win.styles.height = stack_w, stack_h
                    win.styles.offset = (master_w, i * stack_h)

    async def action_open_terminal(self, auto_tfetch=False) -> None:
        if self.is_locked: return
        target_ws = self.query_one(f"#ws-{self.current_ws}")
        term = FloatingTerminal(ws_owner=self.current_ws, classes="floating-win" if self.is_floating else "tiling-win")
        target_ws.mount(term)
        self.call_after_refresh(self.retile_dwm)
        self.call_after_refresh(term.query_one("#term-input").focus)
        if auto_tfetch: self.call_after_refresh(self.run_initial_tfetch, term)

    def action_open_tfiler(self) -> None:
        if self.is_locked: return
        with self.suspend(): os.system("ranger")
        self.post_notification("Welcome Back, Bre!")
        self.refresh()
        self.retile_dwm()

    def run_initial_tfetch(self, term):
        log = term.query_one("#term-log")
        log.update(f"{str(log.content)}\ntoss#nixos $ tfetch\n[bold #a6e22e]TOSS OS v0.1[/]\n[#555555]WS:[/] {self.current_ws}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        if not cmd: return
        term_widget = event.input.parent.parent
        log = term_widget.query_one("#term-log")
        if cmd.lower() == "tosser": cmd = "links https://duckduckgo.com/lite"
        if cmd.lower() == "tfiler": cmd = "ranger"
        base_cmd = cmd.split()[0].lower()
        if base_cmd in ["vi", "vim", "ranger", "htop", "ytfzf", "links", "elinks", "w3m"]:
            log.update(f"{str(log.content)}\ntoss#nixos $ {cmd}")
            with self.suspend(): os.system(cmd)
            self.post_notification("Welcome Back, Bre!")
            self.refresh()
        elif base_cmd == "exit":
            term_widget.remove()
            self.call_after_refresh(self.retile_dwm)
        else:
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                log.update(f"{str(log.content)}\ntoss#nixos $ {cmd}\n{res.stdout}{res.stderr}")
            except: pass
        event.input.value = ""
        log.scroll_end(animate=False)

    def action_close_active_window(self) -> None:
        try:
            ws = self.query_one(f"#ws-{self.current_ws}")
            windows = [w for w in ws.children if isinstance(w, FloatingTerminal)]
            if windows:
                windows[-1].remove()
                self.call_after_refresh(self.retile_dwm)
        except: pass

    def action_toggle_float(self) -> None:
        self.is_floating = not self.is_floating
        ws = self.query_one(f"#ws-{self.current_ws}")
        for win in ws.children:
            if isinstance(win, FloatingTerminal): win.set_classes("floating-win" if self.is_floating else "tiling-win")
        self.call_after_refresh(self.retile_dwm)

    def action_toggle_menu(self) -> None: self.query_one("#start-menu").toggle_class("show")
    def action_switch_ws(self, ws_num: int) -> None:
        self.current_ws = ws_num
        self.query_one("#ws-1").set_class(ws_num != 1, "hidden")
        self.query_one("#ws-2").set_class(ws_num != 2, "hidden")
        self.query_one("#btn-ws1").classes = "ws-active" if ws_num == 1 else "ws-inactive"
        self.query_one("#btn-ws2").classes = "ws-active" if ws_num == 2 else "ws-inactive"
        self.retile_dwm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "wall-black": self.query_one("#desktop").styles.background = "#0a0a0a"
        if event.button.id == "wall-grey": self.query_one("#desktop").styles.background = "#1a1b26"
        if event.button.id == "btn-lock": self.action_lock_screen()
        if event.button.id == "btn-wifi": 
            self.action_hide_all()
            self.action_open_wifi_manager()
            return
        if event.button.id == "btn-brivol": 
            self.query_one("#brivol-menu").add_class("show")
            self.query_one("#brivol-menu").focus()
            self.query_one("#start-menu").remove_class("show")
            return
        if event.button.id == "btn-quit": self.exit()
        self.action_hide_all()

    def action_lock_screen(self) -> None:
        self.is_locked = True
        self.query_one("#lock-screen").add_class("show")
        self.action_hide_all()

    def action_unlock(self) -> None:
        self.is_locked = False
        self.query_one("#lock-screen").remove_class("show")

    def on_key(self, event: Key) -> None:
        if self.is_locked and event.key in ("space", "enter"): self.action_unlock()

    def action_toggle_wallpaper(self) -> None: self.query_one("#wallpaper-menu").toggle_class("show")
    def action_hide_all(self) -> None:
        self.query_one("#start-menu").remove_class("show")
        self.query_one("#wallpaper-menu").remove_class("show")
        self.query_one("#brivol-menu").remove_class("show")

def main(): TOSS().run()
if __name__ == "__main__": main()

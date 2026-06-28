import os
import time
import threading
import queue
import urllib.parse
import urllib.request
import json
import ctypes
import asyncio
import tempfile
import subprocess
import re
import random
from ctypes import wintypes
import tkinter as tk
import tkinter.messagebox as messagebox
from PIL import Image, ImageDraw, ImageTk, ImageGrab
import pystray
from pystray import MenuItem as item
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode, Controller
import winocr

# Hotkey configuration (Virtual Key Codes)
VK_REPLACE = 0x51  # Q -> Translate & Replace
VK_SHOW = 0x45     # E -> Translate & Show Selected Text
VK_GRAB = 0x47     # G -> Translate & Show Screen Area (OCR)

# Global state
pressed_modifiers = set()
active_triggers = set()
current_popup = None
grabber_active = False
ocr_installed_state = False
ocr_in_progress = False
ocr_progress_type = "install"
tray_icon = None

gui_queue = queue.Queue()
root = None

VK_A = 0x41
VK_C = 0x43
VK_V = 0x56
VK_X = 0x58
VK_LCONTROL = 0x11
VK_BACK = 0x08

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]

def press_key(vk):
    user32.keybd_event(vk, 0, 0, 0)

def release_key(vk):
    user32.keybd_event(vk, 0, 2, 0)

def send_key_stroke(vk):
    press_key(vk)
    time.sleep(0.04)  # 40ms hold time for maximum reliability in game loops
    release_key(vk)

class ScreenGrabber:
    def __init__(self, parent, on_selected_callback):
        self.on_selected_callback = on_selected_callback
        self.screenshot = ImageGrab.grab(all_screens=True)
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.bind("<Destroy>", self.on_destroy)
        self.window.attributes("-topmost", True)
        self.window.attributes("-fullscreen", True)
        self.window.attributes("-alpha", 0.99)
        self.window.configure(bg="black")
        
        w, h = self.screenshot.size
        self.window.geometry(f"{w}x{h}+0+0")
        
        self.tk_image = ImageTk.PhotoImage(self.screenshot)
        self.canvas = tk.Canvas(self.window, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.rect = self.canvas.create_rectangle(0, 0, 0, 0, outline="#00bcd4", width=2, state="hidden")
        self.start_x = None
        self.start_y = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.window.bind("<Escape>", lambda e: self.window.destroy())
        
        try:
            self.window.update()
            hwnd = self.window.winfo_id()
            if hwnd:
                style = user32.GetWindowLongW(hwnd, -20)
                user32.SetWindowLongW(hwnd, -20, style | 0x08000000)
        except Exception as e:
            print("Failed to set ScreenGrabber window style:", e)
            
        self.window.update()
        self.window.deiconify()
        self.window.focus_force()
        
    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.canvas.itemconfig(self.rect, state="normal")
        self.canvas.coords(self.rect, self.start_x, self.start_y, self.start_x, self.start_y)
        
    def on_move_press(self, event):
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
        
    def on_button_release(self, event):
        end_x, end_y = event.x, event.y
        self.window.destroy()
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        if x2 - x1 > 5 and y2 - y1 > 5:
            cropped = self.screenshot.crop((x1, y1, x2, y2))
            self.on_selected_callback(cropped)
            
    def on_destroy(self, event):
        if event.widget == self.window:
            global grabber_active
            grabber_active = False

def clean_chat_text(text):
    if not text: return ""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned_lines = []
    bad_keywords = {'игрок', 'вип', 'vip', 'grok', 'rpok', 'грок', 'bnp', 'bnр', 'гpoк', 'грок', 'грокd', 'grokd', 'rpokd', 'гpokd', 'admin', 'moder', 'helper', 'хелпер'}
    for i, line in enumerate(lines):
        if i == 0 and len(lines) > 1:
            lower_line = line.lower()
            if any(kw in lower_line for kw in bad_keywords): continue
            if len(line) < 16 and re.match(r'^[a-zA-Z0-9_]+$', line): continue
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts[0].strip()) < 30:
                cleaned_lines.append(parts[1].strip())
                continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()

def perform_ocr(image):
    async def recognize_dual():
        text_en, text_ru = "", ""
        try:
            res_en = await winocr.recognize_pil(image, 'en')
            if res_en and res_en.text: text_en = res_en.text.strip()
        except: pass
        try:
            res_ru = await winocr.recognize_pil(image, 'ru')
            if res_ru and res_ru.text: text_ru = res_ru.text.strip()
        except: pass
        if is_russian(text_ru): return text_ru
        return text_en if text_en else text_ru
    try:
        return asyncio.run(recognize_dual())
    except: return ""

def get_clipboard_text_safe():
    try:
        for _ in range(15):  # Increased retries to 15 (150ms) for stability
            if user32.OpenClipboard(None):
                try:
                    if user32.IsClipboardFormatAvailable(13):
                        h_clip_mem = user32.GetClipboardData(13)
                        if h_clip_mem:
                            p_clip_mem = kernel32.GlobalLock(h_clip_mem)
                            if p_clip_mem:
                                try:
                                    text = ctypes.c_wchar_p(p_clip_mem).value
                                    return text if text else ""
                                finally:
                                    kernel32.GlobalUnlock(h_clip_mem)
                finally:
                    user32.CloseClipboard()
            time.sleep(0.01)
    except Exception as e:
        print("Clipboard read error:", e)
    return ""

def set_clipboard_text_safe(text):
    try:
        for _ in range(15):  # Increased retries to 15 (150ms) for stability
            if user32.OpenClipboard(None):
                try:
                    user32.EmptyClipboard()
                    text_bytes = (text + "\0").encode('utf-16le')
                    h_global = kernel32.GlobalAlloc(0x0042, len(text_bytes))
                    if h_global:
                        p_global = kernel32.GlobalLock(h_global)
                        if p_global:
                            ctypes.memmove(p_global, text_bytes, len(text_bytes))
                            kernel32.GlobalUnlock(h_global)
                            user32.SetClipboardData(13, h_global)
                            return True
                finally:
                    user32.CloseClipboard()
            time.sleep(0.01)
    except Exception as e:
        print("Clipboard write error:", e)
    return False

def is_russian(text):
    if not text: return False
    cyrillic_chars = sum(1 for char in text if u'\u0400' <= char <= u'\u04FF')
    total_letters = sum(1 for char in text if char.isalpha())
    if total_letters == 0: return False
    return (cyrillic_chars / total_letters) > 0.6

def get_selected_text_game_safe(timeout_ms=1000, cut=False):
    marker = f"__QT_MARKER_{random.randint(100000, 999999)}__"
    if not set_clipboard_text_safe(marker):
        return None
        
    press_key(VK_LCONTROL)
    time.sleep(0.04)
    vk_key = VK_X if cut else VK_C
    press_key(vk_key)
    time.sleep(0.04)
    release_key(vk_key)
    time.sleep(0.04)
    release_key(VK_LCONTROL)
    
    time.sleep(timeout_ms / 1000.0)
    
    text = get_clipboard_text_safe().strip()
    if text and text != marker:
        return text
        
    return None

def translate_text(text, auto_detect=False):
    if not text: return ""
    try:
        is_ru = is_russian(text)
        if auto_detect:
            source = 'ru' if is_ru else 'auto'
            target = 'en' if is_ru else 'ru'
        else:
            source = 'ru' if is_ru else 'en'
            target = 'en' if is_ru else 'ru'
            
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source}&tl={target}&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                html = response.read().decode('utf-8')
                data = json.loads(html)
                return "".join([item[0] for item in data[0] if item[0]])
            else:
                return f"Error: HTTP {response.status}"
    except Exception as e:
        return f"Translation Error: {str(e)}"

def translate_and_replace():
    try:
        while (user32.GetAsyncKeyState(VK_REPLACE) & 0x8000):
            time.sleep(0.01)
            
        original_clipboard = get_clipboard_text_safe()
        
        # Use Cut (VK_X) instead of Copy. This bypasses mods that copy without selection.
        # If nothing is selected, Ctrl+X does absolutely nothing, ensuring we don't false-positive.
        text = get_selected_text_game_safe(timeout_ms=80, cut=True)
        
        if text:
            # Case A: User selected some words manually.
            # No Backspace needed since Ctrl+X already cut the text!
            translated = translate_text(text, auto_detect=False)
            if not translated or translated.startswith("Translation Error"):
                set_clipboard_text_safe(text)
                time.sleep(0.04)
                press_key(VK_LCONTROL)
                time.sleep(0.04)
                press_key(VK_V)
                time.sleep(0.04)
                release_key(VK_V)
                time.sleep(0.04)
                release_key(VK_LCONTROL)
            else:
                set_clipboard_text_safe(translated)
                time.sleep(0.04)
                press_key(VK_LCONTROL)
                time.sleep(0.04)
                press_key(VK_V)
                time.sleep(0.04)
                release_key(VK_V)
                time.sleep(0.04)
                release_key(VK_LCONTROL)
                
        else:
            # Case B: Nothing was selected. Translate the ENTIRE input field.
            press_key(VK_LCONTROL)
            time.sleep(0.04)
            press_key(VK_A)
            time.sleep(0.04)
            release_key(VK_A)
            time.sleep(0.04)
            release_key(VK_LCONTROL)
            time.sleep(0.04)
            
            # Cut everything!
            text = get_selected_text_game_safe(timeout_ms=150, cut=True)
            if not text:
                set_clipboard_text_safe(original_clipboard)
                return
                
            # No Backspace needed since Ctrl+X already cut everything!
            translated = translate_text(text, auto_detect=False)
            if not translated or translated.startswith("Translation Error"):
                set_clipboard_text_safe(text)
                time.sleep(0.04)
                press_key(VK_LCONTROL)
                time.sleep(0.04)
                press_key(VK_V)
                time.sleep(0.04)
                release_key(VK_V)
                time.sleep(0.04)
                release_key(VK_LCONTROL)
            else:
                set_clipboard_text_safe(translated)
                time.sleep(0.04)
                press_key(VK_LCONTROL)
                time.sleep(0.04)
                press_key(VK_V)
                time.sleep(0.04)
                release_key(VK_V)
                time.sleep(0.04)
                release_key(VK_LCONTROL)
                
        time.sleep(0.08)
        set_clipboard_text_safe(original_clipboard)
    finally:
        active_triggers.discard(VK_REPLACE)

def start_mouse_listener(popup):
    def on_click(x, y, button, pressed):
        if pressed:
            try:
                if not popup.winfo_exists(): return False
                px, py = popup.winfo_x(), popup.winfo_y()
                pw, ph = popup.winfo_width(), popup.winfo_height()
                if not (px <= x <= px + pw and py <= y <= py + ph):
                    gui_queue.put(popup.close_popup)
                    return False
            except: return False
    listener = mouse.Listener(on_click=on_click)
    listener.start()
    popup.mouse_listener = listener

def show_popup_loading():
    global current_popup
    if current_popup:
        try: current_popup.destroy()
        except: pass
    popup = tk.Toplevel(root)
    current_popup = popup
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.attributes("-alpha", 0.0)
    bg_color, text_color, border_color = "#1f1f1f", "#f3f3f3", "#333333"
    popup.configure(bg=border_color)
    outer_frame = tk.Frame(popup, bg=border_color, bd=0)
    outer_frame.pack(fill="both", expand=True, padx=1, pady=1)
    frame = tk.Frame(outer_frame, bg=bg_color, padx=16, pady=12)
    frame.pack(fill="both", expand=True)
    body_label = tk.Label(frame, text="Translating...", font=("Segoe UI", 11, "italic"), fg="#888888", bg=bg_color, justify="left", wraplength=380)
    body_label.pack(anchor="w")
    x, y = popup.winfo_pointerxy()
    popup.geometry(f"+{x+15}+{y+15}")
    
    def fade_in(alpha=0.0):
        if alpha < 0.95:
            alpha += 0.15
            popup.attributes("-alpha", alpha)
            popup.after(15, fade_in, alpha)
        else: popup.attributes("-alpha", 0.95)
    fade_in()
    
    is_closing = False
    def close_popup(event=None):
        nonlocal is_closing
        if is_closing: return
        is_closing = True
        if hasattr(popup, 'mouse_listener'):
            try: popup.mouse_listener.stop()
            except: pass
        def fade_out(alpha=0.95):
            if alpha > 0.0:
                alpha -= 0.15
                popup.attributes("-alpha", alpha)
                popup.after(15, fade_out, alpha)
            else:
                try: popup.destroy()
                except: pass
        fade_out()
        
    popup.bind("<Button-1>", close_popup)
    popup.bind("<Key>", close_popup)
    try:
        popup.update_idletasks()
        hwnd = popup.winfo_id()
        if hwnd:
            style = user32.GetWindowLongW(hwnd, -20)
            user32.SetWindowLongW(hwnd, -20, style | 0x08000000)
    except: pass
    
    popup.body_label = body_label
    popup.bg_color = bg_color
    popup.text_color = text_color
    popup.close_popup = close_popup
    start_mouse_listener(popup)
    return popup

def update_popup_content(popup, translated):
    if not popup or not tk.Tk.winfo_exists(popup): return
    popup.body_label.config(text=translated, font=("Segoe UI", 11), fg=popup.text_color)
    popup.update_idletasks()
    width, height = popup.winfo_reqwidth(), popup.winfo_reqheight()
    x, y = popup.winfo_pointerxy()
    sw, sh = popup.winfo_screenwidth(), popup.winfo_screenheight()
    px, py = x + 15, y + 15
    if px + width > sw: px = x - width - 15
    if py + height > sh: py = y - height - 15
    popup.geometry(f"{width}x{height}+{px}+{py}")

def translate_and_show():
    try:
        while (user32.GetAsyncKeyState(VK_SHOW) & 0x8000):
            time.sleep(0.01)
            
        original_clipboard = get_clipboard_text_safe()
        # 150ms timeout is plenty of time for Ctrl+C to register without causing a long delay
        text = get_selected_text_game_safe(timeout_ms=150, cut=False)
        set_clipboard_text_safe(original_clipboard)
        
        # If nothing is selected, silently abort before showing any popup
        if not text:
            return
            
        # Now that we know text is selected, show the loading popup
        popup_container = []
        def create_popup():
            try: popup_container.append(show_popup_loading())
            except: pass
        gui_queue.put(create_popup)
        time.sleep(0.01)
        
        translated = translate_text(text, auto_detect=True)
        if popup_container:
            gui_queue.put(lambda: update_popup_content(popup_container[0], translated))
    finally:
        active_triggers.discard(VK_SHOW)

def on_screen_selected(cropped_image):
    threading.Thread(target=process_ocr_and_translate, args=(cropped_image,), daemon=True).start()

def process_ocr_and_translate(image):
    popup_container = []
    def create_popup():
        try: popup_container.append(show_popup_loading())
        except: pass
    gui_queue.put(create_popup)
    time.sleep(0.01)
    
    text = perform_ocr(image)
    if not text:
        if popup_container: gui_queue.put(popup_container[0].close_popup)
        return
    cleaned_text = clean_chat_text(text)
    if not cleaned_text: cleaned_text = text
    translated = translate_text(cleaned_text, auto_detect=True)
    if popup_container:
        gui_queue.put(lambda: update_popup_content(popup_container[0], translated))

def translate_and_show_screen():
    global grabber_active
    try:
        if grabber_active: return
        grabber_active = True
        time.sleep(0.05)
        def launch_grabber():
            try: ScreenGrabber(root, on_screen_selected)
            except: 
                global grabber_active
                grabber_active = False
        gui_queue.put(launch_grabber)
    finally:
        active_triggers.discard(VK_GRAB)

def on_press(key):
    global pressed_modifiers, active_triggers
    if key == Key.esc:
        if current_popup:
            try:
                if current_popup.winfo_exists(): gui_queue.put(current_popup.close_popup)
            except: pass
        return
    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        pressed_modifiers.add('ctrl')
        return
    vk = getattr(key, 'vk', None)
    if not vk: return
    if 'ctrl' in pressed_modifiers:
        if vk == VK_REPLACE and VK_REPLACE not in active_triggers:
            active_triggers.add(VK_REPLACE)
            threading.Thread(target=translate_and_replace, daemon=True).start()
        elif vk == VK_SHOW and VK_SHOW not in active_triggers:
            active_triggers.add(VK_SHOW)
            threading.Thread(target=translate_and_show, daemon=True).start()
        elif vk == VK_GRAB and VK_GRAB not in active_triggers:
            active_triggers.add(VK_GRAB)
            threading.Thread(target=translate_and_show_screen, daemon=True).start()

def on_release(key):
    global pressed_modifiers, active_triggers
    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        pressed_modifiers.discard('ctrl')
    vk = getattr(key, 'vk', None)
    if vk in active_triggers:
        active_triggers.discard(vk)

def on_exit(icon, item):
    icon.stop()
    gui_queue.put(root.quit)

def create_tray_icon():
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse([4, 4, 60, 60], fill='#0078d7')
    dc.line([20, 20, 44, 20], fill='white', width=6)
    dc.line([32, 20, 32, 46], fill='white', width=6)
    return image

def get_ocr_menu_text(item):
    global ocr_in_progress, ocr_progress_type
    if ocr_in_progress:
        return "Установка пакетов OCR (подождите)..." if ocr_progress_type == "install" else "Удаление пакетов OCR (подождите)..."
    return "Удалить пакеты OCR" if ocr_installed_state else "Установить пакеты OCR"

def is_ocr_menu_enabled(item):
    return not ocr_in_progress

def update_tray_menu():
    global tray_icon
    if tray_icon:
        tray_icon.menu = pystray.Menu(
            item(get_ocr_menu_text, handle_ocr_action, enabled=is_ocr_menu_enabled),
            item("Exit", on_exit)
        )

def handle_ocr_action(icon, item):
    global ocr_installed_state, ocr_in_progress, ocr_progress_type
    if ocr_in_progress: return
    ocr_in_progress = True
    if ocr_installed_state:
        ocr_progress_type = "uninstall"
        gui_queue.put(update_tray_menu)
        threading.Thread(target=run_background_uninstall, daemon=True).start()
    else:
        ocr_progress_type = "install"
        gui_queue.put(update_tray_menu)
        threading.Thread(target=run_background_install, daemon=True).start()

def show_topmost_info(title, message):
    temp = tk.Toplevel()
    temp.withdraw()
    temp.attributes("-topmost", True)
    messagebox.showinfo(title, message, parent=temp)
    temp.destroy()

def show_topmost_error(title, message):
    temp = tk.Toplevel()
    temp.withdraw()
    temp.attributes("-topmost", True)
    messagebox.showerror(title, message, parent=temp)
    temp.destroy()

def run_background_install():
    global ocr_installed_state, ocr_in_progress
    try:
        subprocess.run(["powershell", "-Command", "Add-WindowsCapability -Online -Name Language.OCR~~~en-US~0.0.1.0"], capture_output=True, text=True, creationflags=0x08000000)
        subprocess.run(["powershell", "-Command", "Add-WindowsCapability -Online -Name Language.OCR~~~ru-RU~0.0.1.0"], capture_output=True, text=True, creationflags=0x08000000)
        ocr_installed_state = True
        gui_queue.put(lambda: show_topmost_info("Quick Translator", "Компоненты OCR успешно установлены!"))
    except Exception as e:
        gui_queue.put(lambda: show_topmost_error("Quick Translator", f"Ошибка установки: {e}"))
    finally:
        ocr_in_progress = False
        gui_queue.put(update_tray_menu)

def run_background_uninstall():
    global ocr_installed_state, ocr_in_progress
    try:
        subprocess.run(["powershell", "-Command", "Remove-WindowsCapability -Online -Name Language.OCR~~~en-US~0.0.1.0"], capture_output=True, text=True, creationflags=0x08000000)
        subprocess.run(["powershell", "-Command", "Remove-WindowsCapability -Online -Name Language.OCR~~~ru-RU~0.0.1.0"], capture_output=True, text=True, creationflags=0x08000000)
        ocr_installed_state = False
        gui_queue.put(lambda: show_topmost_info("Quick Translator", "Компоненты OCR успешно удалены!"))
    except Exception as e:
        gui_queue.put(lambda: show_topmost_error("Quick Translator", f"Ошибка удаления: {e}"))
    finally:
        ocr_in_progress = False
        gui_queue.put(update_tray_menu)

def run_tray():
    global tray_icon
    menu = pystray.Menu(
        item(get_ocr_menu_text, handle_ocr_action, enabled=is_ocr_menu_enabled),
        item("Exit", on_exit)
    )
    tray_icon = pystray.Icon("translator", create_tray_icon(), "Quick Translator", menu)
    tray_icon.run()

def process_gui_queue():
    try:
        while True:
            task = gui_queue.get_nowait()
            task()
    except queue.Empty: pass
    except: pass
    root.after(50, process_gui_queue)

def are_ocr_packs_installed():
    img = Image.new('RGB', (100, 100), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), "A", fill="black")
    async def test_lang(lang):
        try:
            await winocr.recognize_pil(img, lang)
            return True
        except: return False
    try:
        return asyncio.run(test_lang('en')) and asyncio.run(test_lang('ru'))
    except: return False

def check_and_install_ocr_startup():
    global ocr_installed_state
    ocr_installed_state = are_ocr_packs_installed()
    gui_queue.put(update_tray_menu)
    if not ocr_installed_state:
        temp_root = tk.Tk()
        temp_root.withdraw()
        install = messagebox.askyesno(
            "Quick Translator",
            "На вашем компьютере не установлены компоненты Windows OCR (распознавание текста).\n\n"
            "Установить их автоматически? Это требуется только один раз и займет около 1-2 минут."
        )
        temp_root.destroy()
        if install:
            global ocr_in_progress, ocr_progress_type
            ocr_in_progress = True
            ocr_progress_type = "install"
            gui_queue.put(update_tray_menu)
            threading.Thread(target=run_background_install, daemon=True).start()

def main():
    global root
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    threading.Thread(target=run_tray, daemon=True).start()
    time.sleep(0.1)
    check_and_install_ocr_startup()
    root = tk.Tk()
    root.withdraw()
    root.after(50, process_gui_queue)
    print("Translator is running. Press Ctrl+Q to translate & replace, Ctrl+E to translate & show, Ctrl+G to translate screen area.")
    try: root.mainloop()
    except: pass
    finally: os._exit(0)

if __name__ == "__main__":
    main()

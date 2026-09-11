# VDI Toolkit - Main Entry Point
# Combined: Clipboard Paste, Auto Clicker, Notification Overlay

import threading
from queue import Empty, Queue

from startup_diagnostics import create_hidden_root, print_startup_report, run_startup_checks
from settings import config


def main():
    print("=" * 40)
    print("  VDI Toolkit - Starting...")
    print("=" * 40)

    issues = run_startup_checks()
    if issues:
        print_startup_report(issues)
        return 1

    try:
        root = create_hidden_root()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1

    from auto_clicker import AutoClicker
    from ai_screenshot import AIScreenshotAssistant
    from clipboard_paste import ClipboardPaste
    from notification import NotificationManager
    from tray_menu import TrayMenu
    from ui_app import ToolkitUI

    notifier = NotificationManager(root)
    ui = None
    status_queue = Queue()
    ui_action_queue = Queue()
    app_running = True

    configured_hotkeys = {
        "paste": config.get("paste_hotkey"),
        "pause": config.get("pause_hotkey"),
        "clicker": config.get("clicker_hotkey"),
        "AI": config.get("ai_hotkey"),
    }
    hotkey_owners = {}
    for owner, hotkey in configured_hotkeys.items():
        hotkey_owners.setdefault(hotkey, []).append(owner)
    for hotkey, owners in hotkey_owners.items():
        if len(owners) > 1:
            print(f"[WARNING] Hotkey {hotkey.upper()} is assigned to: {', '.join(owners)}")

    def on_status(msg, msg_type="info"):
        print(f"[{msg_type.upper()}] {msg}")
        status_queue.put((msg, msg_type))

    def dispatch_to_ui(callback):
        ui_action_queue.put(callback)

    def drain_ui_action_queue():
        while True:
            try:
                callback = ui_action_queue.get_nowait()
            except Empty:
                break
            try:
                callback()
            except Exception as exc:
                on_status(f"UI action failed: {exc}", "error")

        if app_running:
            root.after(50, drain_ui_action_queue)

    def drain_status_queue():
        while True:
            try:
                msg, msg_type = status_queue.get_nowait()
            except Empty:
                break

            app_name = "VDI Toolkit"
            lowered = msg.lower()
            if "paste" in lowered or "mode" in lowered:
                app_name = "Paste"
            elif "click" in lowered or "area" in lowered:
                app_name = "Clicker"
            elif "ai" in lowered or "screenshot" in lowered or "gemini" in lowered or "openai" in lowered:
                app_name = "AI"

            # Progress is intended for the control center, not a toast per character batch.
            if msg_type != "progress":
                notifier.show(app_name, msg)
            if ui:
                ui.update_status_from_module(msg, msg_type)

        if app_running:
            root.after(50, drain_status_queue)

    clipboard = ClipboardPaste(on_status=on_status)
    print(f"OK Clipboard Paste ready ({config.get('paste_hotkey').upper()})")

    clicker = AutoClicker(root, on_status=on_status, dispatch=dispatch_to_ui)
    print(f"OK Auto Clicker ready ({config.get('clicker_hotkey').upper()})")

    ai_assistant = AIScreenshotAssistant(root, on_status=on_status, dispatch=dispatch_to_ui)
    print(f"OK AI Screenshot ready ({config.get('ai_hotkey').upper()})")
    print("OK Notifications ready")

    ui = ToolkitUI(root, clipboard, clicker, ai_assistant, notifier, on_exit=None)
    root.after(50, drain_status_queue)
    root.after(50, drain_ui_action_queue)

    tray = None
    shutdown_started = False

    def on_exit():
        nonlocal app_running, shutdown_started
        if shutdown_started:
            return
        shutdown_started = True
        app_running = False
        print("\nShutting down VDI Toolkit...")
        clipboard.cleanup()
        clicker.cleanup()
        ai_assistant.cleanup()
        if tray:
            tray.stop()
        root.quit()
        root.destroy()

    ui.on_exit = on_exit
    tray = TrayMenu(clipboard, clicker, ai_assistant, ui, notifier, on_exit, dispatch=dispatch_to_ui)
    threading.Thread(target=tray.run, daemon=True).start()

    print("\n" + "=" * 40)
    print("  VDI Toolkit Running!")
    print("=" * 40)
    print("\nHotkeys:")
    print(f"  {config.get('paste_hotkey').upper():<15} - Paste clipboard")
    print(f"  {config.get('pause_hotkey').upper():<15} - Pause/resume paste")
    print(f"  {config.get('clicker_hotkey').upper():<15} - Toggle auto clicker")
    print(f"  {config.get('ai_hotkey').upper():<15} - Capture screenshot and ask AI")
    print("  ESC             - Cancel paste / stop clicking")
    print("\nRight-click tray icon for menu.")

    notifier.show(
        "VDI Toolkit",
        "Started",
        (
            f"{config.get('paste_hotkey').upper()} paste | "
            f"{config.get('clicker_hotkey').upper()} clicker | "
            f"{config.get('ai_hotkey').upper()} AI"
        ),
    )

    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_exit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

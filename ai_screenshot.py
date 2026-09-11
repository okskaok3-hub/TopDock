import base64
import io
import json
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from tkinter import scrolledtext, ttk

import keyboard
from PIL import ImageGrab

from settings import ConfigValidationError, config


def image_to_png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_openai_payload(model, system_prompt, user_prompt, image_bytes):
    image_data = base64.b64encode(image_bytes).decode("ascii")
    prompt = user_prompt.strip() or "Analyze this screenshot."
    return {
        "model": model,
        "instructions": system_prompt.strip(),
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_data}",
                        "detail": "high",
                    },
                ],
            }
        ],
    }


def build_gemini_payload(system_prompt, user_prompt, image_bytes):
    prompt = user_prompt.strip() or "Analyze this screenshot."
    return {
        "system_instruction": {
            "parts": [
                {"text": system_prompt.strip()},
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                ],
            }
        ],
    }


def extract_openai_text(response_data):
    if isinstance(response_data.get("output_text"), str) and response_data["output_text"].strip():
        return response_data["output_text"].strip()

    output_parts = []
    for item in response_data.get("output", []):
        if item.get("type") != "message":
            continue
        for content_item in item.get("content", []):
            text_value = content_item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                output_parts.append(text_value.strip())

    if output_parts:
        return "\n\n".join(output_parts)

    raise RuntimeError("OpenAI returned no text output")


def extract_gemini_text(response_data):
    candidates = response_data.get("candidates") or []
    output_parts = []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts", []):
            text_value = part.get("text")
            if isinstance(text_value, str) and text_value.strip():
                output_parts.append(text_value.strip())

    if output_parts:
        return "\n\n".join(output_parts)

    prompt_feedback = response_data.get("promptFeedback") or {}
    block_reason = prompt_feedback.get("blockReason")
    if block_reason:
        raise RuntimeError(f"Gemini blocked the request: {block_reason}")

    raise RuntimeError("Gemini returned no text output")


def extract_error_message(exc):
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        if body:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return f"HTTP {exc.code}: {body}"

            for path in (
                ("error", "message"),
                ("error",),
                ("message",),
            ):
                current = payload
                for key in path:
                    if isinstance(current, dict):
                        current = current.get(key)
                    else:
                        current = None
                        break
                if isinstance(current, str) and current.strip():
                    return f"HTTP {exc.code}: {current.strip()}"
        return f"HTTP {exc.code}: {exc.reason}"
    return str(exc)


class AIScreenshotAssistant:
    def __init__(self, root, on_status=None, dispatch=None):
        self.root = root
        self.on_status = on_status or (lambda msg, msg_type="info": print(msg))
        self.dispatch = dispatch or (lambda callback: root.after(0, callback))
        self.settings_window = None
        self.result_window = None
        self.hotkey_handler = None
        self.busy = False
        self.reload_from_config()
        self.register_hotkeys()

    def register_hotkeys(self):
        self.unregister_hotkeys()
        self.hotkey_handler = keyboard.add_hotkey(self.hotkey, self.trigger_capture)

    def unregister_hotkeys(self):
        try:
            if self.hotkey_handler is not None:
                keyboard.remove_hotkey(self.hotkey_handler)
                self.hotkey_handler = None
        except Exception:
            pass

    def reload_from_config(self):
        self.provider = config.get("ai_provider", "openai")
        self.hotkey = config.get("ai_hotkey", "ctrl+shift+a")
        self.system_prompt = config.get(
            "ai_system_prompt",
            "Analyze the screenshot and answer clearly using the visible information.",
        )
        self.openai_api_key = config.get("openai_api_key", "")
        self.openai_model = config.get("openai_model", "gpt-4.1-mini")
        self.gemini_api_key = config.get("gemini_api_key", "")
        self.gemini_model = config.get("gemini_model", "gemini-2.5-flash")

    def update_settings(
        self,
        *,
        provider=None,
        hotkey=None,
        system_prompt=None,
        openai_api_key=None,
        openai_model=None,
        gemini_api_key=None,
        gemini_model=None,
    ):
        updates = {}
        if provider is not None:
            updates["ai_provider"] = provider
        if hotkey is not None:
            updates["ai_hotkey"] = hotkey
        if system_prompt is not None:
            updates["ai_system_prompt"] = system_prompt
        if openai_api_key is not None:
            updates["openai_api_key"] = openai_api_key
        if openai_model is not None:
            updates["openai_model"] = openai_model
        if gemini_api_key is not None:
            updates["gemini_api_key"] = gemini_api_key
        if gemini_model is not None:
            updates["gemini_model"] = gemini_model

        if updates:
            config.update(updates)
            self.reload_from_config()
            self.register_hotkeys()

    def trigger_capture(self):
        self.dispatch(self.capture_and_ask)
        return True

    def capture_and_ask(self):
        if self.busy:
            self.on_status("AI screenshot request already running", "warning")
            return False

        api_key = self._get_active_api_key()
        if not api_key:
            self.on_status(f"Set the {self.provider.upper()} API key in AI Screenshot settings", "warning")
            self.open_settings_dialog()
            return False

        try:
            screenshot = self._capture_screenshot()
        except Exception as exc:
            self.on_status(f"Screenshot failed: {exc}", "error")
            return False

        user_prompt = self._ask_for_prompt()
        if user_prompt is None:
            self.on_status("AI screenshot cancelled", "info")
            return False

        self.busy = True
        self.on_status(f"Sending screenshot to {self.provider.upper()}...", "info")
        threading.Thread(
            target=self._request_ai_response,
            args=(image_to_png_bytes(screenshot), user_prompt),
            daemon=True,
        ).start()
        return True

    def _capture_screenshot(self):
        try:
            return ImageGrab.grab(all_screens=True)
        except TypeError:
            return ImageGrab.grab()

    def _ask_for_prompt(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("AI Screenshot Prompt")
        dialog.transient(self.root)
        dialog.attributes("-topmost", True)
        dialog.geometry("640x420")
        dialog.minsize(520, 360)

        ttk.Label(
            dialog,
            text=f"Provider: {self.provider.upper()} | Hotkey: {self.hotkey.upper()}",
        ).pack(fill="x", padx=16, pady=(16, 8))

        ttk.Label(dialog, text="Saved Prompt").pack(anchor="w", padx=16)
        saved_prompt = scrolledtext.ScrolledText(dialog, height=6, wrap="word")
        saved_prompt.pack(fill="both", expand=False, padx=16, pady=(4, 12))
        saved_prompt.insert("1.0", self.system_prompt)
        saved_prompt.configure(state="disabled")

        ttk.Label(dialog, text="Additional Prompt").pack(anchor="w", padx=16)
        prompt_box = scrolledtext.ScrolledText(dialog, height=7, wrap="word")
        prompt_box.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        prompt_box.focus_set()

        result = {"value": None}

        def submit():
            result["value"] = prompt_box.get("1.0", "end").strip()
            dialog.destroy()

        def cancel():
            result["value"] = None
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side="right")
        ttk.Button(button_frame, text="Send", command=submit).pack(side="right", padx=(0, 8))

        dialog.bind("<Control-Return>", lambda _event: submit())
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.wait_visibility()
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result["value"]

    def _request_ai_response(self, image_bytes, user_prompt):
        try:
            if self.provider == "openai":
                response_text = self._call_openai(image_bytes, user_prompt)
            else:
                response_text = self._call_gemini(image_bytes, user_prompt)
        except Exception as exc:
            message = extract_error_message(exc)
            self.dispatch(lambda: self.on_status(f"AI request failed: {message}", "error"))
        else:
            self.dispatch(lambda: self._show_result(response_text))
            self.dispatch(lambda: self.on_status(f"{self.provider.upper()} response ready", "success"))
        finally:
            self.busy = False

    def _call_openai(self, image_bytes, user_prompt):
        payload = build_openai_payload(
            self.openai_model,
            self.system_prompt,
            user_prompt,
            image_bytes,
        )
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            response_data = json.load(response)
        return extract_openai_text(response_data)

    def _call_gemini(self, image_bytes, user_prompt):
        payload = build_gemini_payload(self.system_prompt, user_prompt, image_bytes)
        model = self.gemini_model
        if not model.startswith("models/"):
            model = f"models/{model}"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?"
            f"key={urllib.parse.quote(self.gemini_api_key)}"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            response_data = json.load(response)
        return extract_gemini_text(response_data)

    def _show_result(self, response_text):
        if self.result_window and self.result_window.winfo_exists():
            self.result_window.destroy()

        self.result_window = tk.Toplevel(self.root)
        self.result_window.title("AI Screenshot Result")
        self.result_window.geometry("760x520")
        self.result_window.minsize(560, 360)

        ttk.Label(
            self.result_window,
            text=f"{self.provider.upper()} response",
        ).pack(anchor="w", padx=16, pady=(16, 8))

        output_box = scrolledtext.ScrolledText(self.result_window, wrap="word")
        output_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        output_box.insert("1.0", response_text)

        def copy_output():
            self.root.clipboard_clear()
            self.root.clipboard_append(output_box.get("1.0", "end").strip())
            self.on_status("AI response copied to clipboard", "success")

        button_frame = ttk.Frame(self.result_window)
        button_frame.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Button(button_frame, text="Copy", command=copy_output).pack(side="right")
        ttk.Button(
            button_frame,
            text="Close",
            command=self.result_window.destroy,
        ).pack(side="right", padx=(0, 8))

    def open_settings_dialog(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title("AI Screenshot Settings")
        window.geometry("700x560")
        window.minsize(620, 520)
        self.settings_window = window

        provider_var = tk.StringVar(value=self.provider)
        hotkey_var = tk.StringVar(value=self.hotkey)
        openai_model_var = tk.StringVar(value=self.openai_model)
        gemini_model_var = tk.StringVar(value=self.gemini_model)
        openai_key_var = tk.StringVar(value=self.openai_api_key)
        gemini_key_var = tk.StringVar(value=self.gemini_api_key)

        container = ttk.Frame(window, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Provider").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            container,
            textvariable=provider_var,
            values=("openai", "gemini"),
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(container, text="Hotkey").grid(row=1, column=0, sticky="w")
        ttk.Entry(container, textvariable=hotkey_var).grid(row=1, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(container, text="OpenAI Model").grid(row=2, column=0, sticky="w")
        ttk.Entry(container, textvariable=openai_model_var).grid(row=2, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(container, text="OpenAI API Key").grid(row=3, column=0, sticky="w")
        ttk.Entry(container, textvariable=openai_key_var, show="*").grid(row=3, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(container, text="Gemini Model").grid(row=4, column=0, sticky="w")
        ttk.Entry(container, textvariable=gemini_model_var).grid(row=4, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(container, text="Gemini API Key").grid(row=5, column=0, sticky="w")
        ttk.Entry(container, textvariable=gemini_key_var, show="*").grid(row=5, column=1, sticky="ew", pady=(0, 12))

        ttk.Label(container, text="Saved Prompt").grid(row=6, column=0, sticky="nw")
        prompt_box = scrolledtext.ScrolledText(container, height=14, wrap="word")
        prompt_box.grid(row=6, column=1, sticky="nsew", pady=(0, 12))
        prompt_box.insert("1.0", self.system_prompt)

        container.columnconfigure(1, weight=1)
        container.rowconfigure(6, weight=1)

        button_row = ttk.Frame(container)
        button_row.grid(row=7, column=0, columnspan=2, sticky="e")

        def close():
            self.settings_window = None
            window.destroy()

        def save():
            try:
                self.update_settings(
                    provider=provider_var.get(),
                    hotkey=hotkey_var.get(),
                    system_prompt=prompt_box.get("1.0", "end").strip(),
                    openai_api_key=openai_key_var.get().strip(),
                    openai_model=openai_model_var.get().strip(),
                    gemini_api_key=gemini_key_var.get().strip(),
                    gemini_model=gemini_model_var.get().strip(),
                )
            except ConfigValidationError as exc:
                self.on_status(f"AI settings error: {exc}", "error")
                return

            self.on_status("AI screenshot settings saved", "success")
            close()

        ttk.Button(button_row, text="Cancel", command=close).pack(side="right")
        ttk.Button(button_row, text="Save", command=save).pack(side="right", padx=(0, 8))
        window.protocol("WM_DELETE_WINDOW", close)

    def _get_active_api_key(self):
        if self.provider == "openai":
            return self.openai_api_key.strip()
        return self.gemini_api_key.strip()

    def cleanup(self):
        self.unregister_hotkeys()
        if self.settings_window and self.settings_window.winfo_exists():
            try:
                self.settings_window.destroy()
            except Exception:
                pass
        if self.result_window and self.result_window.winfo_exists():
            try:
                self.result_window.destroy()
            except Exception:
                pass

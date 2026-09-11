using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Text;

namespace TopDock;

public readonly record struct TypingResult(bool Success, int CharacterCount, string Message);

public static class HostClipboardTyper
{
    public static string PrepareText(string text, out int skipped)
    {
        var output = new StringBuilder();
        skipped = 0;
        foreach (var rune in text.Replace("\r\n", "\n").Replace('\r', '\n').EnumerateRunes())
        {
            if (rune.Value is 9 or 10 || rune.Value is >= 32 and <= 126)
                output.Append(rune.ToString());
            else
                skipped++;
        }
        return output.ToString();
    }
    private const uint KeyeventfKeyup = 0x0002;
    private const uint KeyeventfUnicode = 0x0004;
    private const uint InputKeyboard = 1;
    private const byte VirtualKeyShift = 0x10;
    private const byte VirtualKeyControl = 0x11;
    private const byte VirtualKeyAlt = 0x12;
    private const byte VirtualKeyLeftShift = 0xA0;
    private const byte VirtualKeyRightShift = 0xA1;
    private const byte VirtualKeyLeftControl = 0xA2;
    private const byte VirtualKeyRightControl = 0xA3;
    private const byte VirtualKeyLeftAlt = 0xA4;
    private const byte VirtualKeyRightAlt = 0xA5;

    public static string SettingsDescription
    {
        get
        {
            var settings = LoadSettings();
            return $"{settings.CharacterDelayMs} ms character delay, {settings.PressDurationMs} ms key press";
        }
    }

    public static Task<TypingResult> TypeTextAsync(string text, CancellationToken cancellationToken = default)
    {
        return Task.Run(() => TypeText(text, cancellationToken), cancellationToken);
    }

    private static TypingResult TypeText(string text, CancellationToken cancellationToken)
    {
        if (string.IsNullOrEmpty(text))
            return new TypingResult(false, 0, "Host clipboard is empty");

        var settings = LoadSettings();
        var normalized = PrepareText(text, out var skipped);
        if (normalized.Length == 0)
            return new TypingResult(false, 0, $"No sendable text; skipped {skipped} unsupported symbols");
        var typed = 0;

        try
        {
            foreach (var character in normalized)
            {
                cancellationToken.ThrowIfCancellationRequested();
                NeutralizeModifiers(settings.PressDurationMs, cancellationToken);
                TypeCharacter(character, settings.PressDurationMs, cancellationToken);
                typed++;

                if (character == '\n')
                {
                    // Code editors commonly insert indentation automatically after Enter.
                    // Remove only that generated whitespace before typing the clipboard's
                    // own leading spaces, otherwise indentation accumulates on every line.
                    Wait(Math.Max(settings.CharacterDelayMs, 40), cancellationToken);
                    ClearGeneratedLineIndent(settings.PressDurationMs, cancellationToken);
                }

                Wait(settings.CharacterDelayMs, cancellationToken);
            }

            return new TypingResult(true, typed, $"Pasted {typed:N0} characters" +
                (skipped > 0 ? $"; skipped {skipped:N0} unsupported symbols" : " into VDI"));
        }
        catch (OperationCanceledException)
        {
            return new TypingResult(false, typed, $"VDI paste cancelled after {typed:N0} characters");
        }
        catch (Exception exception)
        {
            return new TypingResult(false, typed, $"VDI paste stopped: {exception.Message}");
        }
    }

    private static void ClearGeneratedLineIndent(int pressDurationMs, CancellationToken cancellationToken)
    {
        const byte virtualKeyHome = 0x24;
        const byte virtualKeyDelete = 0x2E;

        // Shift+Home selects any indentation between the editor's new-line caret
        // and column zero. Delete is a safe no-op when the caret is already at zero.
        TapVirtualKey(
            virtualKeyHome,
            shift: true,
            control: false,
            alt: false,
            pressDurationMs,
            cancellationToken);
        TapVirtualKey(
            virtualKeyDelete,
            shift: false,
            control: false,
            alt: false,
            pressDurationMs,
            cancellationToken);
        NeutralizeModifiers(Math.Max(pressDurationMs, 30), cancellationToken);
    }

    private static void TypeCharacter(char character, int pressDurationMs, CancellationToken cancellationToken)
    {
        byte specialKey = character switch
        {
            '\n' => 0x0D,
            '\t' => 0x09,
            '\b' => 0x08,
            _ => 0
        };

        if (specialKey != 0)
        {
            TapVirtualKey(specialKey, false, false, false, pressDurationMs, cancellationToken);
            return;
        }

        var keyInfo = VkKeyScan(character);
        if (keyInfo == -1)
        {
            SendUnicodeCharacter(character);
            return;
        }

        var virtualKey = (byte)(keyInfo & 0xFF);
        var modifierState = (keyInfo >> 8) & 0xFF;
        TapVirtualKey(
            virtualKey,
            shift: (modifierState & 1) != 0,
            control: (modifierState & 2) != 0,
            alt: (modifierState & 4) != 0,
            pressDurationMs,
            cancellationToken);
    }

    private static void TapVirtualKey(
        byte virtualKey,
        bool shift,
        bool control,
        bool alt,
        int pressDurationMs,
        CancellationToken cancellationToken)
    {
        var modifiers = new List<byte>(3);
        if (control) modifiers.Add(VirtualKeyControl);
        if (alt) modifiers.Add(VirtualKeyAlt);
        if (shift) modifiers.Add(VirtualKeyShift);

        foreach (var modifier in modifiers)
            keybd_event(modifier, 0, 0, UIntPtr.Zero);

        keybd_event(virtualKey, 0, 0, UIntPtr.Zero);
        var cancelled = pressDurationMs > 0 && cancellationToken.WaitHandle.WaitOne(pressDurationMs);
        keybd_event(virtualKey, 0, KeyeventfKeyup, UIntPtr.Zero);

        for (var index = modifiers.Count - 1; index >= 0; index--)
            ReleaseModifierFamily(modifiers[index]);

        if (modifiers.Count > 0)
        {
            // Citrix/RDP can lag behind the host input queue. Repeating modifier-up
            // events and allowing them to settle prevents Shift from leaking into
            // the following lowercase letters or punctuation.
            foreach (var modifier in modifiers)
                ReleaseModifierFamily(modifier);
            Wait(Math.Max(pressDurationMs, 30), cancellationToken);
        }

        if (cancelled)
            cancellationToken.ThrowIfCancellationRequested();
    }

    private static void NeutralizeModifiers(int pressDurationMs, CancellationToken cancellationToken)
    {
        ReleaseModifierFamily(VirtualKeyShift);
        ReleaseModifierFamily(VirtualKeyControl);
        ReleaseModifierFamily(VirtualKeyAlt);
        Wait(Math.Clamp(pressDurationMs, 10, 30), cancellationToken);
    }

    private static void ReleaseModifierFamily(byte modifier)
    {
        keybd_event(modifier, 0, KeyeventfKeyup, UIntPtr.Zero);

        switch (modifier)
        {
            case VirtualKeyShift:
                keybd_event(VirtualKeyLeftShift, 0, KeyeventfKeyup, UIntPtr.Zero);
                keybd_event(VirtualKeyRightShift, 0, KeyeventfKeyup, UIntPtr.Zero);
                break;
            case VirtualKeyControl:
                keybd_event(VirtualKeyLeftControl, 0, KeyeventfKeyup, UIntPtr.Zero);
                keybd_event(VirtualKeyRightControl, 0, KeyeventfKeyup, UIntPtr.Zero);
                break;
            case VirtualKeyAlt:
                keybd_event(VirtualKeyLeftAlt, 0, KeyeventfKeyup, UIntPtr.Zero);
                keybd_event(VirtualKeyRightAlt, 0, KeyeventfKeyup, UIntPtr.Zero);
                break;
        }
    }

    private static void SendUnicodeCharacter(char character)
    {
        var inputs = new[]
        {
            new Input
            {
                Type = InputKeyboard,
                Data = new InputUnion
                {
                    Keyboard = new KeyboardInput { Scan = character, Flags = KeyeventfUnicode }
                }
            },
            new Input
            {
                Type = InputKeyboard,
                Data = new InputUnion
                {
                    Keyboard = new KeyboardInput { Scan = character, Flags = KeyeventfUnicode | KeyeventfKeyup }
                }
            }
        };

        if (SendInput((uint)inputs.Length, inputs, Marshal.SizeOf<Input>()) != inputs.Length)
            throw new InvalidOperationException($"Could not type Unicode character U+{(int)character:X4}");
    }

    private static void Wait(int milliseconds, CancellationToken cancellationToken)
    {
        if (milliseconds > 0 && cancellationToken.WaitHandle.WaitOne(milliseconds))
            cancellationToken.ThrowIfCancellationRequested();
    }

    private static TypingSettings LoadSettings()
    {
        var characterDelay = 50;
        var pressDuration = 20;

        try
        {
            var configPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "VDIToolkit",
                "config.json");
            if (File.Exists(configPath))
            {
                using var document = JsonDocument.Parse(File.ReadAllText(configPath));
                if (document.RootElement.TryGetProperty("char_delay", out var delayValue))
                    characterDelay = ToMilliseconds(delayValue.GetDouble(), 0, 5000);
                if (document.RootElement.TryGetProperty("press_duration", out var pressValue))
                    pressDuration = ToMilliseconds(pressValue.GetDouble(), 1, 1000);
            }
        }
        catch { }

        return new TypingSettings(characterDelay, pressDuration);
    }

    private static int ToMilliseconds(double seconds, int minimum, int maximum) =>
        Math.Clamp((int)Math.Round(seconds * 1000), minimum, maximum);

    private readonly record struct TypingSettings(int CharacterDelayMs, int PressDurationMs);

    [StructLayout(LayoutKind.Sequential)]
    private struct Input
    {
        public uint Type;
        public InputUnion Data;
    }

    [StructLayout(LayoutKind.Explicit)]
    private struct InputUnion
    {
        [FieldOffset(0)] public KeyboardInput Keyboard;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct KeyboardInput
    {
        public ushort VirtualKey;
        public ushort Scan;
        public uint Flags;
        public uint Time;
        public UIntPtr ExtraInfo;
    }

    [DllImport("user32.dll")] private static extern void keybd_event(byte virtualKey, byte scanCode, uint flags, UIntPtr extraInfo);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern short VkKeyScan(char character);
    [DllImport("user32.dll", SetLastError = true)] private static extern uint SendInput(uint inputCount, Input[] inputs, int inputSize);
}

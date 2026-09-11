using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace TopDock;

public static class WindowService
{
    private const int GwlExstyle = -20;
    private const long WsExToolwindow = 0x00000080L;
    private const long WsExAppwindow = 0x00040000L;
    private const uint GaRootowner = 3;
    private const uint GwEnabledpopup = 6;
    private const int DwmwaCloaked = 14;
    private const uint WmGeticon = 0x007F;
    private const int IconSmall2 = 2;
    private const int IconSmall = 0;
    private const int GclpHiconsm = -34;
    private const int SwRestore = 9;
    private const uint WmClose = 0x0010;
    private const uint SmtoAbortifhung = 0x0002;

    public static List<WindowEntry> GetWindows(IntPtr ownHandle)
    {
        var result = new List<WindowEntry>();
        var foreground = GetForegroundWindow();
        var shell = GetShellWindow();

        EnumWindows((handle, _) =>
        {
            if (handle == ownHandle || handle == shell || !IsAltTabWindow(handle))
                return true;

            var length = GetWindowTextLength(handle);
            if (length <= 0)
                return true;

            var titleBuilder = new StringBuilder(length + 1);
            GetWindowText(handle, titleBuilder, titleBuilder.Capacity);
            var title = titleBuilder.ToString().Trim();
            if (string.IsNullOrWhiteSpace(title))
                return true;

            GetWindowThreadProcessId(handle, out var processId);
            string processName;
            try
            {
                using var process = Process.GetProcessById((int)processId);
                processName = process.ProcessName;
            }
            catch { processName = "Application"; }

            result.Add(new WindowEntry
            {
                Handle = handle,
                Title = title,
                ProcessName = FriendlyProcessName(processName),
                Icon = GetWindowIcon(handle),
                IsActive = handle == foreground
            });

            return true;
        }, IntPtr.Zero);

        return result
            .OrderByDescending(w => w.IsActive)
            .ThenBy(w => w.ProcessName, StringComparer.CurrentCultureIgnoreCase)
            .ThenBy(w => w.Title, StringComparer.CurrentCultureIgnoreCase)
            .ToList();
    }

    private static bool IsAltTabWindow(IntPtr handle)
    {
        if (!IsWindowVisible(handle))
            return false;

        if (DwmGetWindowAttribute(handle, DwmwaCloaked, out var cloaked, sizeof(int)) == 0 && cloaked != 0)
            return false;

        var exStyle = GetWindowLongPtr(handle, GwlExstyle).ToInt64();
        if ((exStyle & WsExToolwindow) != 0 && (exStyle & WsExAppwindow) == 0)
            return false;

        var root = GetAncestor(handle, GaRootowner);
        var last = root;
        while (true)
        {
            var popup = GetLastActivePopup(last);
            if (popup == last)
                break;
            if (IsWindowVisible(popup))
                last = popup;
            else
                break;
        }

        return last == handle;
    }

    private static ImageSource GetWindowIcon(IntPtr handle)
    {
        IntPtr icon = IntPtr.Zero;
        SendMessageTimeout(handle, WmGeticon, new IntPtr(IconSmall2), IntPtr.Zero,
            SmtoAbortifhung, 80, out icon);
        if (icon == IntPtr.Zero)
            SendMessageTimeout(handle, WmGeticon, new IntPtr(IconSmall), IntPtr.Zero,
                SmtoAbortifhung, 80, out icon);
        if (icon == IntPtr.Zero)
            icon = GetClassLongPtr(handle, GclpHiconsm);

        if (icon != IntPtr.Zero)
        {
            try
            {
                var source = Imaging.CreateBitmapSourceFromHIcon(
                    icon, Int32Rect.Empty, BitmapSizeOptions.FromWidthAndHeight(20, 20));
                source.Freeze();
                return source;
            }
            catch { }
        }

        var fallback = new DrawingImage(new GeometryDrawing(
            new SolidColorBrush(System.Windows.Media.Color.FromRgb(148, 163, 184)),
            new System.Windows.Media.Pen(new SolidColorBrush(System.Windows.Media.Color.FromRgb(226, 232, 240)), 1),
            new RectangleGeometry(new Rect(2, 3, 16, 14), 3, 3)));
        fallback.Freeze();
        return fallback;
    }

    private static string FriendlyProcessName(string name) => name.ToLowerInvariant() switch
    {
        "mstsc" => "Remote Desktop",
        "wfica32" => "Citrix Workspace",
        "msedge" => "Microsoft Edge",
        "chrome" => "Google Chrome",
        "brave" => "Brave",
        "chatgpt" => "ChatGPT",
        "explorer" => "File Explorer",
        "notepad" => "Notepad",
        "code" => "Visual Studio Code",
        "devenv" => "Visual Studio",
        "excel" => "Microsoft Excel",
        "winword" => "Microsoft Word",
        "powerpnt" => "Microsoft PowerPoint",
        "outlook" => "Microsoft Outlook",
        "olk" => "Microsoft Outlook",
        "ms-teams" => "Microsoft Teams",
        "teams" => "Microsoft Teams",
        "windowsterminal" => "Windows Terminal",
        "taskmgr" => "Task Manager",
        "applicationframehost" => "Windows App",
        _ => name.Length > 0 ? char.ToUpper(name[0]) + name[1..] : "Application"
    };

    public static void ActivateWindow(IntPtr handle)
    {
        if (IsIconic(handle))
            ShowWindowAsync(handle, SwRestore);

        BringWindowToTop(handle);
        SetForegroundWindow(handle);
    }

    public static void CloseWindow(IntPtr handle) => PostMessage(handle, WmClose, IntPtr.Zero, IntPtr.Zero);

    public static IntPtr ForegroundWindow => GetForegroundWindow();

    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int maxCount);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern IntPtr GetShellWindow();
    [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr hWnd, uint flags);
    [DllImport("user32.dll")] private static extern IntPtr GetLastActivePopup(IntPtr hWnd);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern IntPtr GetWindowLongPtr64(IntPtr hWnd, int index);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongW")] private static extern IntPtr GetWindowLongPtr32(IntPtr hWnd, int index);
    private static IntPtr GetWindowLongPtr(IntPtr hWnd, int index) => IntPtr.Size == 8 ? GetWindowLongPtr64(hWnd, index) : GetWindowLongPtr32(hWnd, index);
    [DllImport("dwmapi.dll")] private static extern int DwmGetWindowAttribute(IntPtr hWnd, int attribute, out int value, int size);
    [DllImport("user32.dll", SetLastError = true)] private static extern IntPtr GetClassLongPtr(IntPtr hWnd, int index);
    [DllImport("user32.dll", SetLastError = true)] private static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern bool ShowWindowAsync(IntPtr hWnd, int command);
    [DllImport("user32.dll")] private static extern bool BringWindowToTop(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
}

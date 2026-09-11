using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows;

namespace TopDock;

public sealed class AutoClickerService : IDisposable
{
    private const uint MouseeventfLeftdown = 0x0002;
    private const uint MouseeventfLeftup = 0x0004;
    private readonly object _gate = new();
    private readonly Random _random = new();
    private CancellationTokenSource? _cancellation;
    private Task? _clickLoop;

    public AutoClickerService(AppSettings settings)
    {
        if (settings.ClickAreaWidth >= 10 && settings.ClickAreaHeight >= 10)
        {
            SelectedArea = new Int32Rect(
                settings.ClickAreaLeft,
                settings.ClickAreaTop,
                settings.ClickAreaWidth,
                settings.ClickAreaHeight);
        }
    }

    public bool IsEnabled { get; private set; }
    public Int32Rect? SelectedArea { get; private set; }
    public event Action? StateChanged;

    public string AreaDescription => SelectedArea is { } area
        ? $"{area.Width} × {area.Height}px at {area.X}, {area.Y}"
        : "No click area selected";

    public string DelayDescription
    {
        get
        {
            var delay = LoadDelayRange();
            return Math.Abs(delay.MinimumSeconds - delay.MaximumSeconds) < 0.01
                ? $"every {delay.MinimumSeconds:0.#} seconds"
                : $"every {delay.MinimumSeconds:0.#}–{delay.MaximumSeconds:0.#} seconds";
        }
    }

    public void SetArea(Int32Rect area)
    {
        if (area.Width < 10 || area.Height < 10)
            throw new ArgumentOutOfRangeException(nameof(area), "Click area must be at least 10 × 10 pixels.");

        SelectedArea = area;
        StateChanged?.Invoke();
    }

    public bool Toggle()
    {
        if (IsEnabled)
        {
            Stop();
            return false;
        }

        return Start();
    }

    public bool Start()
    {
        lock (_gate)
        {
            if (IsEnabled)
                return true;
            if (SelectedArea is null)
                return false;

            IsEnabled = true;
            _cancellation = new CancellationTokenSource();
            _clickLoop = Task.Run(() => RunClickLoopAsync(_cancellation.Token));
        }

        StateChanged?.Invoke();
        return true;
    }

    public void Stop()
    {
        lock (_gate)
        {
            if (!IsEnabled)
                return;
            IsEnabled = false;
            _cancellation?.Cancel();
            _cancellation?.Dispose();
            _cancellation = null;
            _clickLoop = null;
        }

        StateChanged?.Invoke();
    }

    private async Task RunClickLoopAsync(CancellationToken cancellationToken)
    {
        try
        {
            // Give TopDock time to hide and return focus to the VDI.
            await Task.Delay(500, cancellationToken);
            while (!cancellationToken.IsCancellationRequested)
            {
                if (!IsForegroundVdi())
                {
                    await Task.Delay(750, cancellationToken);
                    continue;
                }

                ClickSelectedArea();
                var range = LoadDelayRange();
                var delaySeconds = range.MinimumSeconds >= range.MaximumSeconds
                    ? range.MinimumSeconds
                    : _random.NextDouble() * (range.MaximumSeconds - range.MinimumSeconds) + range.MinimumSeconds;
                await Task.Delay(TimeSpan.FromSeconds(delaySeconds), cancellationToken);
            }
        }
        catch (OperationCanceledException) { }
        catch
        {
            IsEnabled = false;
            StateChanged?.Invoke();
        }
    }

    private void ClickSelectedArea()
    {
        if (SelectedArea is not { } area)
            return;

        var x = _random.Next(area.X, area.X + Math.Max(1, area.Width));
        var y = _random.Next(area.Y, area.Y + Math.Max(1, area.Height));
        GetCursorPos(out var previous);
        SetCursorPos(x, y);
        mouse_event(MouseeventfLeftdown, 0, 0, 0, UIntPtr.Zero);
        Thread.Sleep(38);
        mouse_event(MouseeventfLeftup, 0, 0, 0, UIntPtr.Zero);
        SetCursorPos(previous.X, previous.Y);
    }

    private static bool IsForegroundVdi()
    {
        var handle = GetForegroundWindow();
        if (handle == IntPtr.Zero)
            return false;

        GetWindowThreadProcessId(handle, out var processId);
        try
        {
            using var process = Process.GetProcessById((int)processId);
            return process.ProcessName.Equals("wfica32", StringComparison.OrdinalIgnoreCase) ||
                   process.ProcessName.Equals("mstsc", StringComparison.OrdinalIgnoreCase);
        }
        catch { return false; }
    }

    private static DelayRange LoadDelayRange()
    {
        var minimum = 60d;
        var maximum = 60d;
        try
        {
            var path = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "VDIToolkit",
                "config.json");
            if (File.Exists(path))
            {
                using var document = JsonDocument.Parse(File.ReadAllText(path));
                if (document.RootElement.TryGetProperty("click_delay_min", out var minValue))
                    minimum = minValue.GetDouble();
                if (document.RootElement.TryGetProperty("click_delay_max", out var maxValue))
                    maximum = maxValue.GetDouble();
            }
        }
        catch { }

        minimum = Math.Clamp(minimum, 0.1, 86400);
        maximum = Math.Clamp(maximum, minimum, 86400);
        return new DelayRange(minimum, maximum);
    }

    public void Dispose()
    {
        Stop();
        GC.SuppressFinalize(this);
    }

    private readonly record struct DelayRange(double MinimumSeconds, double MaximumSeconds);

    [StructLayout(LayoutKind.Sequential)]
    private struct Point
    {
        public int X;
        public int Y;
    }

    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
    [DllImport("user32.dll")] private static extern bool GetCursorPos(out Point point);
    [DllImport("user32.dll")] private static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] private static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);
}

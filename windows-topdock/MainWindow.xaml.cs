using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using Forms = System.Windows.Forms;
using WpfButton = System.Windows.Controls.Button;

namespace TopDock;

public partial class MainWindow : Window
{
    private const double DockWindowHeight = 92;
    private const double SettingsWindowHeight = 500;
    private const int HotkeyId = 0x5444;
    private const uint ModAlt = 0x0001;
    private const uint ModControl = 0x0002;
    private const uint WmHotkey = 0x0312;
    private const uint SwpNosize = 0x0001;
    private const uint SwpNomove = 0x0002;
    private const uint SwpNoactivate = 0x0010;
    private const uint SwpShowwindow = 0x0040;
    private static readonly IntPtr HwndTopmost = new(-1);

    private readonly ObservableCollection<WindowEntry> _visibleWindows = [];
    private readonly DispatcherTimer _windowTimer = new() { Interval = TimeSpan.FromMilliseconds(1200) };
    private readonly DispatcherTimer _edgeTimer = new() { Interval = TimeSpan.FromMilliseconds(50) };
    private readonly DispatcherTimer _clockTimer = new() { Interval = TimeSpan.FromSeconds(1) };
    private readonly AppSettings _settings;
    private readonly AutoClickerService _autoClicker;
    private readonly Forms.NotifyIcon _trayIcon;
    private List<WindowEntry> _allWindows = [];
    private IntPtr _handle;
    private bool _isShown;
    private bool _allowClose;
    private DateTime _outsideSince = DateTime.UtcNow;
    private Forms.Screen? _screen;
    private DateTime _lastTopmostPush = DateTime.MinValue;
    private IntPtr _lastExternalForeground;
    private bool _captureBusy;

    public MainWindow()
    {
        InitializeComponent();
        WindowItems.ItemsSource = _visibleWindows;
        _settings = SettingsStore.Load();
        _autoClicker = new AutoClickerService(_settings);
        _autoClicker.StateChanged += () => Dispatcher.BeginInvoke(UpdateAutoClickerAppearance);
        // Remove the legacy VDI Toolkit startup entry created by earlier TopDock builds.
        SettingsStore.RemoveLegacyVdiStartup();

        KeepOpenCheck.IsChecked = _settings.Pinned;
        StartupCheck.IsChecked = _settings.RunAtStartup;
        CompactCheck.IsChecked = _settings.CompactMode;
        UpdatePinAppearance();
        UpdateStartupAppearance();
        UpdateAutoClickerAppearance();
        ApplyCompactMode();
        PasteButton.ToolTip = $"Type the host clipboard into VDI ({HostClipboardTyper.SettingsDescription})";

        _trayIcon = new Forms.NotifyIcon
        {
            Icon = System.Drawing.Icon.ExtractAssociatedIcon(Environment.ProcessPath ?? string.Empty)
                   ?? System.Drawing.SystemIcons.Application,
            Text = "TopDock — Ctrl+Alt+Space",
            Visible = true
        };
        _trayIcon.DoubleClick += (_, _) => Dispatcher.Invoke(() => Reveal(force: true));
        var menu = new Forms.ContextMenuStrip();
        menu.Items.Add("Show TopDock", null, (_, _) => Dispatcher.Invoke(() => Reveal(force: true)));
        menu.Items.Add("Toggle auto clicker", null, (_, _) => Dispatcher.Invoke(ToggleAutoClicker));
        menu.Items.Add("Select auto-click area", null, (_, _) => Dispatcher.Invoke(SelectAutoClickArea));
        menu.Items.Add("Settings", null, (_, _) => Dispatcher.Invoke(ShowSettings));
        menu.Items.Add(new Forms.ToolStripSeparator());
        menu.Items.Add("Exit", null, (_, _) => Dispatcher.Invoke(ExitApplication));
        _trayIcon.ContextMenuStrip = menu;

        Loaded += MainWindow_Loaded;
        SourceInitialized += MainWindow_SourceInitialized;
        Closing += MainWindow_Closing;

        _windowTimer.Tick += (_, _) =>
        {
            RefreshWindows();
        };
        _edgeTimer.Tick += (_, _) => TrackPointer();
        _clockTimer.Tick += (_, _) => UpdateClock();
    }

    private void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        UpdateClock();
        RefreshWindows();
        PositionForScreen(Forms.Screen.FromPoint(Forms.Cursor.Position), animate: false);
        Reveal(force: true);
        _outsideSince = DateTime.UtcNow.AddSeconds(1);
        _windowTimer.Start();
        _edgeTimer.Start();
        _clockTimer.Start();
    }

    private void MainWindow_SourceInitialized(object? sender, EventArgs e)
    {
        _handle = new WindowInteropHelper(this).Handle;
        HwndSource.FromHwnd(_handle)?.AddHook(WndProc);
        RegisterHotKey(_handle, HotkeyId, ModControl | ModAlt, (uint)KeyInterop.VirtualKeyFromKey(Key.Space));
    }

    private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WmHotkey && wParam.ToInt32() == HotkeyId)
        {
            if (_isShown) HideDock(); else Reveal(force: true);
            handled = true;
        }
        return IntPtr.Zero;
    }

    private void RefreshWindows()
    {
        var priorHandles = _allWindows.Select(w => w.Handle).ToArray();
        var fresh = WindowService.GetWindows(_handle);
        var activeChanged = _allWindows.FirstOrDefault(w => w.IsActive)?.Handle != fresh.FirstOrDefault(w => w.IsActive)?.Handle;
        var structureChanged = !priorHandles.SequenceEqual(fresh.Select(w => w.Handle));
        _allWindows = fresh;

        if (structureChanged || activeChanged || !string.IsNullOrWhiteSpace(SearchBox.Text))
            ApplyFilter();
    }

    private void ApplyFilter()
    {
        var query = SearchBox.Text.Trim();
        var filtered = string.IsNullOrEmpty(query)
            ? _allWindows
            : _allWindows.Where(w =>
                w.Title.Contains(query, StringComparison.CurrentCultureIgnoreCase) ||
                w.ProcessName.Contains(query, StringComparison.CurrentCultureIgnoreCase)).ToList();

        _visibleWindows.Clear();
        for (var index = 0; index < filtered.Count; index++)
        {
            filtered[index].ShortcutHint = index < 9 ? $"ALT {index + 1}" : string.Empty;
            _visibleWindows.Add(filtered[index]);
        }

        EmptyState.Visibility = filtered.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        WindowCountText.Text = filtered.Count == 1 ? "1 open window" : $"{filtered.Count} open windows";
    }

    private void TrackPointer()
    {
        if (_captureBusy) return;
        var foreground = WindowService.ForegroundWindow;
        if (foreground != IntPtr.Zero && foreground != _handle)
            _lastExternalForeground = foreground;

        var cursor = Forms.Cursor.Position;
        var currentScreen = Forms.Screen.FromPoint(cursor);
        // Full-screen Citrix sessions often reserve or capture the first few rows.
        // A 14 px activation band remains easy to reach while still being unobtrusive.
        var atTopEdge = cursor.Y <= currentScreen.Bounds.Top + 14;

        if (atTopEdge)
        {
            if (_screen?.DeviceName != currentScreen.DeviceName)
                PositionForScreen(currentScreen, animate: false);
            PromoteToTopmost();
            Reveal();
            return;
        }

        if (!_isShown || _settings.Pinned || SettingsPanel.Visibility == Visibility.Visible || SearchPanel.Visibility == Visibility.Visible)
            return;

        var scale = GetScale();
        var leftPx = Left * scale.X;
        var topPx = Top * scale.Y;
        var inside = cursor.X >= leftPx - 12 && cursor.X <= leftPx + ActualWidth * scale.X + 12 &&
                     cursor.Y >= topPx - 10 && cursor.Y <= topPx + ActualHeight * scale.Y + 18;

        if (inside)
        {
            _outsideSince = DateTime.UtcNow;
            PromoteToTopmost();
        }
        else if (DateTime.UtcNow - _outsideSince > TimeSpan.FromMilliseconds(650))
            HideDock();
    }

    private void PositionForScreen(Forms.Screen screen, bool animate)
    {
        _screen = screen;
        var scale = GetScale();
        var screenWidthDip = screen.Bounds.Width / scale.X;
        Width = Math.Clamp(screenWidthDip - 48, 760, 1240);
        Left = screen.Bounds.Left / scale.X + (screenWidthDip - Width) / 2;

        if (!animate)
            Top = _isShown ? GetShownTop() : GetHiddenTop();
    }

    private (double X, double Y) GetScale()
    {
        var source = PresentationSource.FromVisual(this);
        return source?.CompositionTarget is { } target
            ? (target.TransformToDevice.M11, target.TransformToDevice.M22)
            : (1d, 1d);
    }

    private double GetShownTop()
    {
        var scale = GetScale();
        return (_screen?.Bounds.Top ?? 0) / scale.Y + 6;
    }

    private double GetHiddenTop()
    {
        var scale = GetScale();
        return (_screen?.Bounds.Top ?? 0) / scale.Y - ActualHeight + 3;
    }

    private void Reveal(bool force = false)
    {
        if (_captureBusy) return;
        PromoteToTopmost(force: true);
        if (_isShown && !force) return;
        _isShown = true;
        _outsideSince = DateTime.UtcNow;
        AnimateTop(GetShownTop());
        Dispatcher.BeginInvoke(() => PromoteToTopmost(force: true), DispatcherPriority.Loaded);
        RefreshWindows();
    }

    private void PromoteToTopmost(bool force = false)
    {
        if (_captureBusy) return;
        if (_handle == IntPtr.Zero)
            return;

        if (!force && DateTime.UtcNow - _lastTopmostPush < TimeSpan.FromMilliseconds(220))
            return;

        _lastTopmostPush = DateTime.UtcNow;
        SetWindowPos(
            _handle,
            HwndTopmost,
            0,
            0,
            0,
            0,
            SwpNomove | SwpNosize | SwpNoactivate | SwpShowwindow);
    }

    private void HideDock(bool immediate = false)
    {
        if (_settings.Pinned && !immediate) return;
        CloseOverlays(clearSearch: true);
        _isShown = false;
        if (immediate) Top = GetHiddenTop(); else AnimateTop(GetHiddenTop());
    }

    private void AnimateTop(double target)
    {
        var animation = new DoubleAnimation
        {
            To = target,
            Duration = TimeSpan.FromMilliseconds(SystemParameters.ClientAreaAnimation ? 210 : 0),
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };
        BeginAnimation(TopProperty, animation, HandoffBehavior.SnapshotAndReplace);
    }

    private void WindowButton_Click(object sender, RoutedEventArgs e)
    {
        if (sender is WpfButton { Tag: IntPtr handle })
        {
            WindowService.ActivateWindow(handle);
            if (!_settings.Pinned) HideDock();
        }
    }

    private void WindowButton_PreviewMouseDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ChangedButton == MouseButton.Middle && sender is WpfButton { Tag: IntPtr handle })
        {
            WindowService.CloseWindow(handle);
            e.Handled = true;
            Dispatcher.BeginInvoke(RefreshWindows, DispatcherPriority.Background);
        }
    }

    private void WindowScroller_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
    {
        WindowScroller.ScrollToHorizontalOffset(WindowScroller.HorizontalOffset - e.Delta * 0.7);
        e.Handled = true;
    }

    private async void ScreenshotButton_Click(object sender, RoutedEventArgs e)
    {
        if (_captureBusy) return;
        _captureBusy = true;
        _autoClicker.Stop();
        ScreenshotButton.IsEnabled = false;
        HideDock(immediate: true);
        Hide();

        try
        {
            var selector = new ScreenCaptureSelectionWindow();
            if (selector.ShowDialog() != true || selector.SelectedArea is not { } area)
            {
                ShowTransientStatus("Screenshot cancelled");
                return;
            }

            // Let the transparent selector fully leave the desktop before capture.
            await Task.Delay(120);
            var result = ScreenshotService.CaptureRegionToClipboard(area);
            ShowTransientStatus(result.Message);
            _trayIcon.ShowBalloonTip(
                2200,
                result.Success ? "Screenshot copied" : "Screenshot failed",
                result.Message,
                result.Success ? Forms.ToolTipIcon.Info : Forms.ToolTipIcon.Warning);
        }
        catch (Exception exception)
        {
            ShowTransientStatus($"Screenshot failed: {exception.Message}");
        }
        finally
        {
            _captureBusy = false;
            Show();
            Reveal(force: true);
            ScreenshotButton.IsEnabled = true;
        }
    }

    private void SearchButton_Click(object sender, RoutedEventArgs e) => ShowSearch();

    private async void PasteButton_Click(object sender, RoutedEventArgs e)
    {
        string clipboardText;
        try
        {
            clipboardText = System.Windows.Clipboard.ContainsText()
                ? System.Windows.Clipboard.GetText(System.Windows.TextDataFormat.UnicodeText)
                : string.Empty;
            if (string.IsNullOrEmpty(clipboardText))
            {
                ShowTransientStatus("Host clipboard has no text to paste");
                return;
            }
        }
        catch
        {
            ShowTransientStatus("Clipboard is temporarily unavailable");
            return;
        }

        var target = _allWindows.FirstOrDefault(window =>
                         window.ProcessName.Equals("Citrix Workspace", StringComparison.OrdinalIgnoreCase) ||
                         window.ProcessName.Equals("Remote Desktop", StringComparison.OrdinalIgnoreCase))?.Handle;
        if (target is null or 0)
        {
            ShowTransientStatus("Open a Citrix or Remote Desktop session first");
            return;
        }

        PasteButton.IsEnabled = false;
        ShowTransientStatus($"Typing {clipboardText.Length:N0} host clipboard characters into VDI");
        if (!_settings.Pinned)
            HideDock();

        try
        {
            WindowService.ActivateWindow(target.Value);
            await Task.Delay(220);
            var result = await HostClipboardTyper.TypeTextAsync(clipboardText);
            _trayIcon.ShowBalloonTip(
                2400,
                result.Success ? "TopDock paste complete" : "TopDock paste stopped",
                result.Message,
                result.Success ? Forms.ToolTipIcon.Info : Forms.ToolTipIcon.Warning);
        }
        finally
        {
            PasteButton.IsEnabled = true;
        }
    }

    private void AutoClickButton_Click(object sender, RoutedEventArgs e) => ToggleAutoClicker();

    private void ToggleAutoClicker()
    {
        if (_autoClicker.SelectedArea is null)
        {
            ShowTransientStatus("Select an auto-click area with the adjacent gear first");
            return;
        }

        var enabled = _autoClicker.Toggle();
        UpdateAutoClickerAppearance();
        ShowTransientStatus(enabled
            ? $"Auto clicker ON — {_autoClicker.DelayDescription} while VDI is active"
            : "Auto clicker OFF");

        if (enabled)
        {
            if (!_settings.Pinned)
                HideDock();
            var vdi = _allWindows.FirstOrDefault(window =>
                window.ProcessName.Equals("Citrix Workspace", StringComparison.OrdinalIgnoreCase) ||
                window.ProcessName.Equals("Remote Desktop", StringComparison.OrdinalIgnoreCase));
            if (vdi is not null)
                WindowService.ActivateWindow(vdi.Handle);
        }
    }

    private void AreaButton_Click(object sender, RoutedEventArgs e) => SelectAutoClickArea();

    private void SelectAutoClickArea()
    {
        _autoClicker.Stop();
        UpdateAutoClickerAppearance();
        var screen = Forms.Screen.FromPoint(Forms.Cursor.Position);
        HideDock(immediate: true);

        var selector = new AreaSelectionWindow(screen);
        if (selector.ShowDialog() == true && selector.SelectedArea is { } area)
        {
            _autoClicker.SetArea(area);
            _settings.ClickAreaLeft = area.X;
            _settings.ClickAreaTop = area.Y;
            _settings.ClickAreaWidth = area.Width;
            _settings.ClickAreaHeight = area.Height;
            SaveSettings();
            UpdateAutoClickerAppearance();
            _trayIcon.ShowBalloonTip(
                2200,
                "Auto-click area saved",
                $"{area.Width} × {area.Height}px selected. Use AUTO to turn clicking on.",
                Forms.ToolTipIcon.Info);
        }

        if (_settings.Pinned)
            Reveal(force: true);
    }

    private void StartupButton_Click(object sender, RoutedEventArgs e)
    {
        SetStartupState(!_settings.RunAtStartup);
        StartupCheck.IsChecked = _settings.RunAtStartup;
        ShowTransientStatus(_settings.RunAtStartup
            ? "TopDock will start with Windows"
            : "Windows startup disabled");
    }

    private void ShowSearch()
    {
        Reveal(force: true);
        SettingsPanel.Visibility = Visibility.Collapsed;
        SearchPanel.Visibility = Visibility.Visible;
        SearchBox.Focus();
        Keyboard.Focus(SearchBox);
    }

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        SearchPlaceholder.Visibility = string.IsNullOrEmpty(SearchBox.Text) ? Visibility.Visible : Visibility.Collapsed;
        ApplyFilter();
    }

    private void PinButton_Click(object sender, RoutedEventArgs e)
    {
        _settings.Pinned = !_settings.Pinned;
        KeepOpenCheck.IsChecked = _settings.Pinned;
        SaveSettings();
        UpdatePinAppearance();
        if (_settings.Pinned) Reveal(force: true);
    }

    private void UpdatePinAppearance()
    {
        PinButton.Content = _settings.Pinned ? "\uE77A" : "\uE718";
        PinButton.ToolTip = _settings.Pinned ? "Auto-hide TopDock" : "Keep TopDock open";
        PinButton.Background = _settings.Pinned
            ? new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(48, 200, 0, 223))
            : new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(15, 255, 255, 255));
    }

    private void SettingsButton_Click(object sender, RoutedEventArgs e) => ShowSettings();

    private void ShowSettings()
    {
        Reveal(force: true);
        SearchPanel.Visibility = Visibility.Collapsed;
        SettingsPanel.Visibility = Visibility.Visible;
        Height = SettingsWindowHeight;
    }

    private void CloseSettings_Click(object sender, RoutedEventArgs e)
    {
        SettingsPanel.Visibility = Visibility.Collapsed;
        Height = DockWindowHeight;
        _outsideSince = DateTime.UtcNow;
    }

    private void KeepOpenCheck_Changed(object sender, RoutedEventArgs e)
    {
        if (!IsLoaded) return;
        _settings.Pinned = KeepOpenCheck.IsChecked == true;
        SaveSettings();
        UpdatePinAppearance();
        if (_settings.Pinned) Reveal(force: true);
    }

    private void StartupCheck_Changed(object sender, RoutedEventArgs e)
    {
        if (!IsLoaded) return;
        SetStartupState(StartupCheck.IsChecked == true);
    }

    private void SetStartupState(bool enabled)
    {
        _settings.RunAtStartup = enabled;
        SettingsStore.SetRunAtStartup(enabled);
        SaveSettings();
        UpdateStartupAppearance();
    }

    private void UpdateStartupAppearance()
    {
        StartupButton.Content = _settings.RunAtStartup ? "START ✓" : "STARTUP";
        StartupButton.ToolTip = _settings.RunAtStartup
            ? "TopDock starts with Windows — click to disable"
            : "Start TopDock with Windows";
        StartupButton.Background = new System.Windows.Media.SolidColorBrush(
            _settings.RunAtStartup
                ? System.Windows.Media.Color.FromArgb(48, 22, 163, 74)
                : System.Windows.Media.Color.FromArgb(15, 255, 255, 255));
    }

    private void UpdateAutoClickerAppearance()
    {
        AutoClickLabel.Text = _autoClicker.IsEnabled ? "ON" : "OFF";
        AutoClickButton.ToolTip = _autoClicker.SelectedArea is null
            ? "Select an area with the adjacent gear before turning AUTO on"
            : $"Auto clicker {(_autoClicker.IsEnabled ? "ON" : "OFF")} — {_autoClicker.DelayDescription}";
        AutoClickButton.Background = new System.Windows.Media.SolidColorBrush(
            _autoClicker.IsEnabled
                ? System.Windows.Media.Color.FromArgb(58, 22, 163, 74)
                : _autoClicker.SelectedArea is not null
                    ? System.Windows.Media.Color.FromArgb(28, 139, 92, 246)
                    : System.Windows.Media.Color.FromArgb(15, 255, 255, 255));
        AutoClickButton.BorderBrush = new System.Windows.Media.SolidColorBrush(
            _autoClicker.IsEnabled
                ? System.Windows.Media.Color.FromArgb(88, 22, 163, 74)
                : System.Windows.Media.Color.FromArgb(28, 255, 255, 255));
        AreaButton.ToolTip = $"Select auto-click area — {_autoClicker.AreaDescription}";
        AreaButton.Background = new System.Windows.Media.SolidColorBrush(
            _autoClicker.SelectedArea is not null
                ? System.Windows.Media.Color.FromArgb(26, 139, 92, 246)
                : System.Windows.Media.Color.FromArgb(15, 255, 255, 255));
    }

    private async void ShowTransientStatus(string message)
    {
        ClockText.Text = message;
        await Task.Delay(2600);
        if (!IsLoaded) return;
        UpdateClock();
    }

    private void CompactCheck_Changed(object sender, RoutedEventArgs e)
    {
        if (!IsLoaded) return;
        _settings.CompactMode = CompactCheck.IsChecked == true;
        ApplyCompactMode();
        SaveSettings();
    }

    private void ApplyCompactMode()
    {
        FitWindowCards();
    }

    private void WindowScroller_SizeChanged(object sender, SizeChangedEventArgs e) => FitWindowCards();

    private void FitWindowCards()
    {
        if (_settings is null || WindowScroller.ActualWidth < 1) return;
        var available = WindowScroller.ActualWidth;
        var preferred = _settings.CompactMode ? 124d : 140d;
        var columns = Math.Max(1, (int)Math.Floor(available / (preferred + 6)));
        var cardWidth = Math.Max(40, Math.Floor(available / columns) - 6);
        Resources["WindowCardMinWidth"] = cardWidth;
        Resources["WindowCardMaxWidth"] = cardWidth;
    }

    private void Window_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            if (SettingsPanel.Visibility == Visibility.Visible)
            {
                SettingsPanel.Visibility = Visibility.Collapsed;
                Height = DockWindowHeight;
            }
            else if (SearchPanel.Visibility == Visibility.Visible)
            {
                CloseOverlays(clearSearch: true);
            }
            else
            {
                HideDock();
            }
            e.Handled = true;
        }
        else if (e.Key == Key.F && Keyboard.Modifiers.HasFlag(ModifierKeys.Control))
        {
            ShowSearch();
            e.Handled = true;
        }
        else if (Keyboard.Modifiers.HasFlag(ModifierKeys.Alt) && e.Key is >= Key.D1 and <= Key.D9)
        {
            var index = e.Key - Key.D1;
            if (index < _visibleWindows.Count)
                WindowService.ActivateWindow(_visibleWindows[index].Handle);
            e.Handled = true;
        }
        else if (e.Key == Key.Enter && SearchPanel.Visibility == Visibility.Visible && _visibleWindows.Count > 0)
        {
            WindowService.ActivateWindow(_visibleWindows[0].Handle);
            if (!_settings.Pinned) HideDock();
            e.Handled = true;
        }
    }

    private void CloseOverlays(bool clearSearch)
    {
        SettingsPanel.Visibility = Visibility.Collapsed;
        SearchPanel.Visibility = Visibility.Collapsed;
        Height = DockWindowHeight;
        if (clearSearch) SearchBox.Clear();
    }

    private void UpdateClock() => ClockText.Text = DateTime.Now.ToString("ddd, h:mm tt");

    private void SaveSettings() => SettingsStore.Save(_settings);

    private void ExitButton_Click(object sender, RoutedEventArgs e) => ExitApplication();

    private void ExitApplication()
    {
        _allowClose = true;
        Close();
    }

    private void MainWindow_Closing(object? sender, CancelEventArgs e)
    {
        if (!_allowClose)
        {
            e.Cancel = true;
            HideDock();
            return;
        }

        _windowTimer.Stop();
        _edgeTimer.Stop();
        _clockTimer.Stop();
        _autoClicker.Dispose();
        if (_handle != IntPtr.Zero) UnregisterHotKey(_handle, HotkeyId);
        _trayIcon.Visible = false;
        _trayIcon.Dispose();
        System.Windows.Application.Current.Shutdown();
    }

    [DllImport("user32.dll")] private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint modifiers, uint virtualKey);
    [DllImport("user32.dll")] private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
    [DllImport("user32.dll")] private static extern bool SetWindowPos(IntPtr hWnd, IntPtr insertAfter, int x, int y, int width, int height, uint flags);
}

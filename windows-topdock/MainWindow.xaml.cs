using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
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
    private const double SettingsWindowHeight = 600;
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
    private bool _collapsed;
    private bool _dragging;
    private bool _circleDragging;
    private System.Drawing.Point _dragOrigin;
    private double _dragLeft;
    private double _dragTop;
    private double? _customTop;
    private double? _customLeft;
    private double _clipboardFontSize = 12;
    private double _clipboardImageScale = 1;
    private readonly Dictionary<string, WpfButton> _quickButtons = [];
    private WpfButton? _quickDragSource;
    private System.Drawing.Point _quickDragOrigin;
    private bool _quickDragStarted;

    public MainWindow()
    {
        InitializeComponent();
        WindowItems.ItemsSource = _visibleWindows;
        _settings = SettingsStore.Load();
        _customLeft = _settings.DockLeft;
        _customTop = _settings.DockTop;
        _autoClicker = new AutoClickerService(_settings);
        _autoClicker.StateChanged += () => Dispatcher.BeginInvoke(UpdateAutoClickerAppearance);
        // Remove the legacy VDI Toolkit startup entry created by earlier TopDock builds.
        SettingsStore.RemoveLegacyVdiStartup();
        if (_settings.RunAtStartup)
            SettingsStore.SetRunAtStartup(true);

        KeepOpenCheck.IsChecked = _settings.Pinned;
        StartupCheck.IsChecked = _settings.RunAtStartup;
        CompactCheck.IsChecked = _settings.CompactMode;
        InitializeQuickActions();
        UpdatePinAppearance();
        UpdateStartupAppearance();
        UpdateAutoClickerAppearance();
        ApplyCompactMode();
        PasteButton.ToolTip = $"Type the host clipboard into VDI ({HostClipboardTyper.SettingsDescription})";
        VersionText.Text = "Version 1.3.0";
        ZoomPathBox.Text = ResolveZoomClipboardPath() ?? "ZoomClipboardUI.exe not found";

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

    private void InitializeQuickActions()
    {
        _quickButtons.Add("paste", PasteButton);
        _quickButtons.Add("shot", ScreenshotButton);
        _quickButtons.Add("auto", AutoClickButton);
        _quickButtons.Add("zoom", ZoomButton);
        foreach (var (id, button) in _quickButtons)
        {
            button.Tag = id;
            button.AllowDrop = true;
            button.PreviewMouseLeftButtonDown += QuickAction_MouseDown;
            button.PreviewMouseMove += QuickAction_MouseMove;
            button.DragOver += QuickAction_DragOver;
            button.Drop += QuickAction_Drop;
        }

        var order = (_settings.QuickActionOrder ?? []).Concat(_quickButtons.Keys)
            .Distinct(StringComparer.OrdinalIgnoreCase).Where(_quickButtons.ContainsKey).ToList();
        foreach (var id in order)
        {
            var button = _quickButtons[id];
            QuickActions.Children.Remove(button);
            QuickActions.Children.Insert(QuickActions.Children.IndexOf(SettingsButton), button);
        }
        ApplyQuickActionVisibility();
        PasteVisibleCheck.IsChecked = PasteButton.Visibility == Visibility.Visible;
        ShotVisibleCheck.IsChecked = ScreenshotButton.Visibility == Visibility.Visible;
        AutoVisibleCheck.IsChecked = AutoClickButton.Visibility == Visibility.Visible;
        ZoomVisibleCheck.IsChecked = ZoomButton.Visibility == Visibility.Visible;
    }

    private void ApplyQuickActionVisibility()
    {
        var hidden = new HashSet<string>(_settings.HiddenQuickActions ?? [], StringComparer.OrdinalIgnoreCase);
        foreach (var (id, button) in _quickButtons)
            button.Visibility = hidden.Contains(id) ? Visibility.Collapsed : Visibility.Visible;
    }

    private void QuickActionVisibility_Changed(object sender, RoutedEventArgs e)
    {
        if (!IsLoaded || sender is not System.Windows.Controls.CheckBox { Tag: string id } || !_quickButtons.TryGetValue(id, out var button)) return;
        button.Visibility = ((System.Windows.Controls.CheckBox)sender).IsChecked == true ? Visibility.Visible : Visibility.Collapsed;
        _settings.HiddenQuickActions = _quickButtons
            .Where(pair => pair.Value.Visibility != Visibility.Visible).Select(pair => pair.Key).ToList();
        SaveSettings();
    }

    private void QuickAction_MouseDown(object sender, MouseButtonEventArgs e)
    {
        _quickDragSource = sender as WpfButton;
        _quickDragOrigin = Forms.Cursor.Position;
        _quickDragStarted = false;
    }

    private void QuickAction_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed || _quickDragStarted || _quickDragSource is null) return;
        var pointer = Forms.Cursor.Position;
        if (Math.Abs(pointer.X - _quickDragOrigin.X) + Math.Abs(pointer.Y - _quickDragOrigin.Y) < 7) return;
        _quickDragStarted = true;
        System.Windows.DragDrop.DoDragDrop(_quickDragSource, _quickDragSource.Tag, System.Windows.DragDropEffects.Move);
        _quickDragSource = null;
        _quickDragStarted = false;
    }

    private void QuickAction_DragOver(object sender, System.Windows.DragEventArgs e)
    {
        e.Effects = e.Data.GetData(typeof(string)) is string ? System.Windows.DragDropEffects.Move : System.Windows.DragDropEffects.None;
        e.Handled = true;
    }

    private void QuickAction_Drop(object sender, System.Windows.DragEventArgs e)
    {
        if (sender is not WpfButton target || e.Data.GetData(typeof(string)) is not string sourceId ||
            !_quickButtons.TryGetValue(sourceId, out var source) || source == target) return;
        var after = e.GetPosition(target).X > target.ActualWidth / 2;
        QuickActions.Children.Remove(source);
        var index = QuickActions.Children.IndexOf(target) + (after ? 1 : 0);
        QuickActions.Children.Insert(Math.Min(index, QuickActions.Children.IndexOf(SettingsButton)), source);
        _settings.QuickActionOrder = QuickActions.Children.OfType<WpfButton>()
            .Where(button => button.Tag is string).Select(button => (string)button.Tag).ToList();
        SaveSettings();
        e.Handled = true;
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
        if (_dragging) return;
        var foreground = WindowService.ForegroundWindow;
        if (foreground != IntPtr.Zero && foreground != _handle)
            _lastExternalForeground = foreground;

        var cursor = Forms.Cursor.Position;
        var currentScreen = Forms.Screen.FromPoint(cursor);
        // Full-screen Citrix sessions often reserve or capture the first few rows.
        // A 14 px activation band remains easy to reach while still being unobtrusive.
        var atTopEdge = IsTopActivationEdge(cursor.Y, currentScreen.Bounds.Top);

        if (_collapsed)
        {
            if (atTopEdge) Reveal(force: true);
            return;
        }

        if (atTopEdge)
        {
            if (_screen?.DeviceName != currentScreen.DeviceName)
                PositionForScreen(currentScreen, animate: false);
            PromoteToTopmost();
            Reveal();
            return;
        }

        if (!_isShown || _settings.Pinned || SettingsPanel.Visibility == Visibility.Visible || SearchPanel.Visibility == Visibility.Visible || ClipboardPanel.Visibility == Visibility.Visible)
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
        if (_collapsed) return;
        var scale = GetScale();
        var screenWidthDip = screen.Bounds.Width / scale.X;
        Width = Math.Min(1240, Math.Max(1, screenWidthDip - 24));
        var screenLeft = screen.Bounds.Left / scale.X;
        Left = _customLeft is { } custom
            ? Math.Clamp(custom, screenLeft, Math.Max(screenLeft, screenLeft + screenWidthDip - Width))
            : screenLeft + (screenWidthDip - Width) / 2;

        if (!animate)
            Top = _isShown ? GetShownTop() : GetHiddenTop();
    }

    internal static bool IsTopActivationEdge(int pointerY, int screenTop) =>
        pointerY >= screenTop && pointerY <= screenTop + 18;

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
        return _customTop ?? (_screen?.Bounds.Top ?? 0) / scale.Y + 6;
    }

    private double GetHiddenTop()
    {
        var scale = GetScale();
        return (_screen?.Bounds.Top ?? 0) / scale.Y - ActualHeight + 3;
    }

    private void Reveal(bool force = false)
    {
        if (_captureBusy) return;
        if (_collapsed) ExpandDock();
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
        if (_collapsed) return;
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
            SelectAutoClickArea();
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

    private void ShowSearch()
    {
        Reveal(force: true);
        SettingsPanel.Visibility = Visibility.Collapsed;
        ClipboardPanel.Visibility = Visibility.Collapsed;
        SearchPanel.Visibility = Visibility.Visible;
        SearchBox.Focus();
        Keyboard.Focus(SearchBox);
    }

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        SearchPlaceholder.Visibility = string.IsNullOrEmpty(SearchBox.Text) ? Visibility.Visible : Visibility.Collapsed;
        ApplyFilter();
    }

    private void UpdatePinAppearance()
    {
        KeepOpenCheck.IsChecked = _settings.Pinned;
    }

    private void SettingsButton_Click(object sender, RoutedEventArgs e) => ShowSettings();

    private void ShowSettings()
    {
        Reveal(force: true);
        SearchPanel.Visibility = Visibility.Collapsed;
        ClipboardPanel.Visibility = Visibility.Collapsed;
        SettingsPanel.Visibility = Visibility.Visible;
        var scale = GetScale();
        var screenBottom = (_screen?.WorkingArea.Bottom ?? Forms.Screen.FromPoint(Forms.Cursor.Position).WorkingArea.Bottom) / scale.Y;
        Height = Math.Min(SettingsWindowHeight, Math.Max(320, screenBottom - GetShownTop() - 12));
        SettingsPanel.MaxHeight = Height - 88;
        ZoomPathBox.Text = ResolveZoomClipboardPath() ?? "ZoomClipboardUI.exe not found";
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
        StartupCheck.IsChecked = _settings.RunAtStartup;
    }

    private void UpdateAutoClickerAppearance()
    {
        AutoClickLabel.Text = _autoClicker.IsEnabled ? "ON" : "OFF";
        AutoClickButton.ToolTip = _autoClicker.SelectedArea is null
            ? "Click to select an auto-click area"
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
    }

    private void DragHandle_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (_collapsed) return;
        _dragging = true;
        _dragOrigin = Forms.Cursor.Position;
        _dragLeft = Left;
        _dragTop = Top;
        BeginAnimation(TopProperty, null);
        ((UIElement)sender).CaptureMouse();
        e.Handled = true;
    }

    private void DragHandle_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (!_dragging) return;
        var pointer = Forms.Cursor.Position;
        var scale = GetScale();
        var area = Forms.Screen.FromPoint(pointer).WorkingArea;
        _customLeft = Left = Math.Clamp(_dragLeft + (pointer.X - _dragOrigin.X) / scale.X,
            area.Left / scale.X, Math.Max(area.Left / scale.X, area.Right / scale.X - Width));
        _customTop = Top = Math.Clamp(_dragTop + (pointer.Y - _dragOrigin.Y) / scale.Y,
            area.Top / scale.Y, Math.Max(area.Top / scale.Y, area.Bottom / scale.Y - DockWindowHeight));
        _isShown = true;
    }

    private void DragHandle_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        _dragging = false;
        ((UIElement)sender).ReleaseMouseCapture();
        SaveDockPosition();
    }

    private void CollapseButton_Click(object sender, RoutedEventArgs e)
    {
        CloseOverlays(clearSearch: true);
        BeginAnimation(TopProperty, null);
        _customLeft = Left;
        _customTop = Top;
        _collapsed = true;
        DockSurface.Visibility = Visibility.Collapsed;
        CircleSurface.Visibility = Visibility.Visible;
        Width = 72;
        Height = 72;
        _isShown = true;
    }

    private void ExpandDock()
    {
        _collapsed = false;
        CircleSurface.Visibility = Visibility.Collapsed;
        DockSurface.Visibility = Visibility.Visible;
        Height = DockWindowHeight;
        PositionForScreen(Forms.Screen.FromPoint(Forms.Cursor.Position), animate: false);
    }

    private void CircleButton_Click(object sender, RoutedEventArgs e)
    {
        if (!_circleDragging) Reveal(force: true);
        _circleDragging = false;
    }

    private void CircleButton_MouseDown(object sender, MouseButtonEventArgs e)
    {
        _dragOrigin = Forms.Cursor.Position;
        _dragLeft = Left;
        _dragTop = Top;
        _circleDragging = false;
    }

    private void CircleButton_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed || !_collapsed) return;
        var pointer = Forms.Cursor.Position;
        if (Math.Abs(pointer.X - _dragOrigin.X) + Math.Abs(pointer.Y - _dragOrigin.Y) < 5 && !_circleDragging) return;
        _circleDragging = true;
        var scale = GetScale();
        var area = Forms.Screen.FromPoint(pointer).WorkingArea;
        _customLeft = Left = Math.Clamp(_dragLeft + (pointer.X - _dragOrigin.X) / scale.X,
            area.Left / scale.X, Math.Max(area.Left / scale.X, area.Right / scale.X - Width));
        _customTop = Top = Math.Clamp(_dragTop + (pointer.Y - _dragOrigin.Y) / scale.Y,
            area.Top / scale.Y, Math.Max(area.Top / scale.Y, area.Bottom / scale.Y - Height));
    }

    private void CircleButton_MouseUp(object sender, MouseButtonEventArgs e)
    {
        if (_circleDragging)
        {
            CircleButton.ReleaseMouseCapture();
            SaveDockPosition();
            e.Handled = true;
        }
    }

    private void SaveDockPosition()
    {
        _settings.DockLeft = _customLeft;
        _settings.DockTop = _customTop;
        SaveSettings();
    }

    private string? ResolveZoomClipboardPath() => FindZoomClipboardPath(
        _settings, AppContext.BaseDirectory, Environment.GetFolderPath(Environment.SpecialFolder.UserProfile));

    internal static string? FindZoomClipboardPath(AppSettings settings, string appDirectory, string userProfile)
    {
        var userTool = Path.Combine(userProfile,
            "Downloads", "gemini", "vdi-toolkit", "zoom-clipboard", "release-dashboard-v3", "ZoomClipboardUI.exe");
        var candidates = new[] { settings.ZoomClipboardPath, Path.Combine(appDirectory, "ZoomClipboardUI.exe"), userTool };
        return candidates.FirstOrDefault(path => !string.IsNullOrWhiteSpace(path) && File.Exists(path));
    }

    private void ZoomButton_Click(object sender, RoutedEventArgs e)
    {
        var path = ResolveZoomClipboardPath();
        if (path is null)
        {
            ShowTransientStatus("Zoom Clipboard app not found. Choose it in Settings.");
            return;
        }
        try
        {
            foreach (var running in Process.GetProcessesByName("ZoomClipboardUI"))
            {
                using (running)
                {
                    if (running.MainWindowHandle == IntPtr.Zero) continue;
                    ShowWindow(running.MainWindowHandle, 9);
                    SetForegroundWindow(running.MainWindowHandle);
                    return;
                }
            }
            Process.Start(new ProcessStartInfo(path)
            {
                UseShellExecute = true,
                WorkingDirectory = Path.GetDirectoryName(path) ?? AppContext.BaseDirectory
            });
            ShowTransientStatus("Opening Zoom Clipboard");
        }
        catch (Exception exception)
        {
            ShowTransientStatus($"Zoom Clipboard could not open: {exception.Message}");
        }
    }

    private void BrowseZoomPath_Click(object sender, RoutedEventArgs e)
    {
        var picker = new Microsoft.Win32.OpenFileDialog
        {
            Title = "Choose ZoomClipboardUI.exe",
            Filter = "Zoom Clipboard (ZoomClipboardUI.exe)|ZoomClipboardUI.exe|Applications (*.exe)|*.exe",
            CheckFileExists = true
        };
        if (picker.ShowDialog(this) != true) return;
        _settings.ZoomClipboardPath = picker.FileName;
        ZoomPathBox.Text = picker.FileName;
        SaveSettings();
    }

    private void ClipboardButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (System.Windows.Clipboard.ContainsImage())
            {
                var image = System.Windows.Clipboard.GetImage();
                ClipboardImagePreview.Source = image;
                ClipboardImageScroller.Visibility = Visibility.Visible;
                ClipboardPreview.Visibility = Visibility.Collapsed;
                _clipboardImageScale = image is null ? 1 : Math.Min(1, Math.Min(400 / image.Width, 240 / image.Height));
                SetClipboardZoom(_clipboardFontSize);
            }
            else
            {
                ClipboardPreview.Text = System.Windows.Clipboard.ContainsText()
                    ? System.Windows.Clipboard.GetText(System.Windows.TextDataFormat.UnicodeText)
                    : "Clipboard has no text or image to preview.";
                ClipboardPreview.Visibility = Visibility.Visible;
                ClipboardImageScroller.Visibility = Visibility.Collapsed;
                ClipboardZoomText.Text = $"{_clipboardFontSize / 12:P0}";
            }
        }
        catch
        {
            ClipboardPreview.Text = "Clipboard is temporarily unavailable.";
            ClipboardPreview.Visibility = Visibility.Visible;
            ClipboardImageScroller.Visibility = Visibility.Collapsed;
        }
        SettingsPanel.Visibility = Visibility.Collapsed;
        SearchPanel.Visibility = Visibility.Collapsed;
        ClipboardPanel.Visibility = Visibility.Visible;
        Height = 400;
        Reveal(force: true);
    }

    private void ClipboardZoomIn_Click(object sender, RoutedEventArgs e) => SetClipboardZoom(ClipboardImageScroller.Visibility == Visibility.Visible ? _clipboardImageScale * 1.25 : _clipboardFontSize + 2);
    private void ClipboardZoomOut_Click(object sender, RoutedEventArgs e) => SetClipboardZoom(ClipboardImageScroller.Visibility == Visibility.Visible ? _clipboardImageScale / 1.25 : _clipboardFontSize - 2);
    private void SetClipboardZoom(double size)
    {
        if (ClipboardImageScroller.Visibility == Visibility.Visible)
        {
            _clipboardImageScale = Math.Clamp(size, 0.1, 4);
            ClipboardImagePreview.LayoutTransform = new System.Windows.Media.ScaleTransform(_clipboardImageScale, _clipboardImageScale);
            ClipboardZoomText.Text = $"{_clipboardImageScale:P0}";
        }
        else
        {
            _clipboardFontSize = Math.Clamp(size, 10, 32);
            ClipboardPreview.FontSize = _clipboardFontSize;
            ClipboardZoomText.Text = $"{_clipboardFontSize / 12:P0}";
        }
    }

    private void CloseClipboard_Click(object sender, RoutedEventArgs e)
    {
        ClipboardPanel.Visibility = Visibility.Collapsed;
        Height = DockWindowHeight;
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
        ClipboardPanel.Visibility = Visibility.Collapsed;
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
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr hWnd, int command);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr hWnd);
}

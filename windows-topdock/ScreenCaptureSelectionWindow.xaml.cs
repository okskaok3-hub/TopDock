using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using Forms = System.Windows.Forms;

namespace TopDock;

public partial class ScreenCaptureSelectionWindow : Window
{
    private const uint SwpShowwindow = 0x0040;
    private static readonly IntPtr HwndTopmost = new(-1);
    private readonly System.Drawing.Rectangle _virtualScreen = Forms.SystemInformation.VirtualScreen;
    private System.Windows.Point? _start;
    private System.Drawing.Point _physicalStart;

    public ScreenCaptureSelectionWindow()
    {
        InitializeComponent();
        SourceInitialized += Window_SourceInitialized;
        Loaded += (_, _) => Activate();
    }

    public Int32Rect? SelectedArea { get; private set; }

    private void Window_SourceInitialized(object? sender, EventArgs e)
    {
        var handle = new WindowInteropHelper(this).Handle;
        SetWindowPos(
            handle,
            HwndTopmost,
            _virtualScreen.Left,
            _virtualScreen.Top,
            _virtualScreen.Width,
            _virtualScreen.Height,
            SwpShowwindow);
    }

    private void Canvas_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        _start = e.GetPosition(SelectionCanvas);
        _physicalStart = Forms.Cursor.Position;
        SelectionBorder.Visibility = Visibility.Visible;
        Canvas.SetLeft(SelectionBorder, _start.Value.X);
        Canvas.SetTop(SelectionBorder, _start.Value.Y);
        SelectionBorder.Width = 0;
        SelectionBorder.Height = 0;
        SelectionCanvas.CaptureMouse();
    }

    private void Canvas_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (_start is null || e.LeftButton != MouseButtonState.Pressed)
            return;

        UpdateSelection(e.GetPosition(SelectionCanvas));
    }

    private void Canvas_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (_start is null)
            return;

        var end = e.GetPosition(SelectionCanvas);
        UpdateSelection(end);
        SelectionCanvas.ReleaseMouseCapture();

        var left = Math.Min(_start.Value.X, end.X);
        var top = Math.Min(_start.Value.Y, end.Y);
        var width = Math.Abs(end.X - _start.Value.X);
        var height = Math.Abs(end.Y - _start.Value.Y);
        if (width < 8 || height < 8)
        {
            DialogResult = false;
            Close();
            return;
        }

        var physicalEnd = Forms.Cursor.Position;
        SelectedArea = new Int32Rect(
            Math.Min(_physicalStart.X, physicalEnd.X),
            Math.Min(_physicalStart.Y, physicalEnd.Y),
            Math.Max(8, Math.Abs(physicalEnd.X - _physicalStart.X)),
            Math.Max(8, Math.Abs(physicalEnd.Y - _physicalStart.Y)));
        DialogResult = true;
        Close();
    }

    private void UpdateSelection(System.Windows.Point end)
    {
        if (_start is null)
            return;

        var left = Math.Min(_start.Value.X, end.X);
        var top = Math.Min(_start.Value.Y, end.Y);
        Canvas.SetLeft(SelectionBorder, left);
        Canvas.SetTop(SelectionBorder, top);
        SelectionBorder.Width = Math.Abs(end.X - _start.Value.X);
        SelectionBorder.Height = Math.Abs(end.Y - _start.Value.Y);
    }

    private void Canvas_MouseRightButtonDown(object sender, MouseButtonEventArgs e) => Cancel();

    private void Window_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key != Key.Escape)
            return;

        Cancel();
        e.Handled = true;
    }

    private void Cancel()
    {
        DialogResult = false;
        Close();
    }

    [DllImport("user32.dll")]
    private static extern bool SetWindowPos(
        IntPtr window, IntPtr insertAfter, int x, int y, int width, int height, uint flags);
}

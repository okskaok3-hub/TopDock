using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using Forms = System.Windows.Forms;

namespace TopDock;

public partial class AreaSelectionWindow : Window
{
    private const uint SwpShowwindow = 0x0040;
    private static readonly IntPtr HwndTopmost = new(-1);
    private readonly Forms.Screen _screen;
    private System.Windows.Point? _start;

    public AreaSelectionWindow(Forms.Screen screen)
    {
        _screen = screen;
        InitializeComponent();
        SourceInitialized += AreaSelectionWindow_SourceInitialized;
        Loaded += (_, _) => Activate();
    }

    public Int32Rect? SelectedArea { get; private set; }

    private void AreaSelectionWindow_SourceInitialized(object? sender, EventArgs e)
    {
        var handle = new WindowInteropHelper(this).Handle;
        SetWindowPos(
            handle,
            HwndTopmost,
            _screen.Bounds.Left,
            _screen.Bounds.Top,
            _screen.Bounds.Width,
            _screen.Bounds.Height,
            SwpShowwindow);
    }

    private void Canvas_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        _start = e.GetPosition(SelectionCanvas);
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
        if (width < 10 || height < 10)
        {
            DialogResult = false;
            Close();
            return;
        }

        var physicalTopLeft = PointToScreen(new System.Windows.Point(left, top));
        var physicalBottomRight = PointToScreen(new System.Windows.Point(left + width, top + height));
        SelectedArea = new Int32Rect(
            (int)Math.Round(physicalTopLeft.X),
            (int)Math.Round(physicalTopLeft.Y),
            Math.Max(10, (int)Math.Round(physicalBottomRight.X - physicalTopLeft.X)),
            Math.Max(10, (int)Math.Round(physicalBottomRight.Y - physicalTopLeft.Y)));
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
        if (e.Key == Key.Escape)
        {
            Cancel();
            e.Handled = true;
        }
    }

    private void Cancel()
    {
        DialogResult = false;
        Close();
    }

    [DllImport("user32.dll")] private static extern bool SetWindowPos(
        IntPtr window, IntPtr insertAfter, int x, int y, int width, int height, uint flags);
}

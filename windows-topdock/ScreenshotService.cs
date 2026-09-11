using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media.Imaging;
using System.IO;

namespace TopDock;

public sealed record ScreenshotResult(bool Success, string Message);

public static class ScreenshotService
{
    public static ScreenshotResult CaptureRegionToClipboard(Int32Rect region)
    {
        if (region.Width < 1 || region.Height < 1)
            return new ScreenshotResult(false, "Select a larger screen area");

        try
        {
            using var bitmap = new Bitmap(region.Width, region.Height, PixelFormat.Format24bppRgb);
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.CopyFromScreen(
                    region.X,
                    region.Y,
                    0,
                    0,
                    new System.Drawing.Size(region.Width, region.Height),
                    CopyPixelOperation.SourceCopy);
            }

            var bitmapHandle = bitmap.GetHbitmap();
            try
            {
                var source = Imaging.CreateBitmapSourceFromHBitmap(
                    bitmapHandle,
                    IntPtr.Zero,
                    Int32Rect.Empty,
                    BitmapSizeOptions.FromEmptyOptions());
                source.Freeze();
                SetClipboardImageWithRetry(source);
            }
            finally
            {
                DeleteObject(bitmapHandle);
            }

            return new ScreenshotResult(
                true,
                $"Original PNG copied — {region.Width} × {region.Height}px (no resizing)");
        }
        catch (Exception exception)
        {
            return new ScreenshotResult(false, $"Screenshot failed: {exception.Message}");
        }
    }

    public static MemoryStream EncodeOriginalPng(BitmapSource source)
    {
        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(source));
        var png = new MemoryStream();
        encoder.Save(png);
        png.Position = 0;
        return png;
    }

    private static void SetClipboardImageWithRetry(BitmapSource source)
    {
        // Publish lossless PNG and the standard bitmap without resizing.
        using var png = EncodeOriginalPng(source);
        var data = new System.Windows.DataObject();
        data.SetData(System.Windows.DataFormats.Bitmap, source);
        data.SetData("PNG", png, false);
        Exception? lastError = null;
        for (var attempt = 0; attempt < 5; attempt++)
        {
            try
            {
                png.Position = 0;
                System.Windows.Clipboard.SetDataObject(data, true);
                return;
            }
            catch (ExternalException exception)
            {
                lastError = exception;
                Thread.Sleep(45);
            }
        }

        throw lastError ?? new ExternalException("The Windows clipboard is unavailable");
    }

    [DllImport("gdi32.dll")]
    private static extern bool DeleteObject(IntPtr graphicsObject);
}

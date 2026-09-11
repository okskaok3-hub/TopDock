using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace TopDock;

public static class ContentChecks
{
    public static void Run()
    {
        var text = HostClipboardTyper.PrepareText("const x = \"A→B\";\r\n\treturn x; 😀", out var skipped);
        if (text != "const x = \"AB\";\n\treturn x; " || skipped != 2)
            throw new InvalidOperationException("Unicode skip fidelity failed");
        var ascii = string.Concat(Enumerable.Range(32, 95).Select(i => (char)i)) + "\n\t";
        if (HostClipboardTyper.PrepareText(ascii, out skipped) != ascii || skipped != 0)
            throw new InvalidOperationException("ASCII preservation failed");
        var pixels = new byte[3840 * 2160 * 3];
        pixels[0] = 17; pixels[1] = 93; pixels[2] = 241;
        var source = BitmapSource.Create(3840, 2160, 144, 144, PixelFormats.Bgr24, null, pixels, 3840 * 3);
        using var png = ScreenshotService.EncodeOriginalPng(source);
        var decoded = new PngBitmapDecoder(png, BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad).Frames[0];
        if (decoded.PixelWidth != 3840 || decoded.PixelHeight != 2160)
            throw new InvalidOperationException("4K pixel dimensions changed");
        var output = new byte[pixels.Length];
        decoded.CopyPixels(output, 3840 * 3, 0);
        if (!pixels.SequenceEqual(output))
            throw new InvalidOperationException("PNG pixels changed");
        Console.WriteLine("PASS symbol skipping, ASCII code fidelity, and pixel-exact 3840x2160 PNG roundtrip");
    }
}

using System.Windows.Media;

namespace TopDock;

public sealed class WindowEntry
{
    public required IntPtr Handle { get; init; }
    public required string Title { get; init; }
    public required string ProcessName { get; init; }
    public required ImageSource Icon { get; init; }
    public bool IsActive { get; init; }
    public string ShortcutHint { get; set; } = string.Empty;
}

public sealed class AppSettings
{
    public bool Pinned { get; set; }
    public bool RunAtStartup { get; set; }
    public bool CompactMode { get; set; }
    public int ClickAreaLeft { get; set; }
    public int ClickAreaTop { get; set; }
    public int ClickAreaWidth { get; set; }
    public int ClickAreaHeight { get; set; }
}

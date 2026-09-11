using System.IO;
using System.Text.Json;
using Microsoft.Win32;

namespace TopDock;

public static class SettingsStore
{
    private const string RunKeyPath = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string RunValueName = "TopDock";
    private static readonly string Folder = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TopDock");
    private static readonly string FilePath = Path.Combine(Folder, "settings.json");

    public static AppSettings Load()
    {
        try
        {
            if (File.Exists(FilePath))
                return JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(FilePath)) ?? new AppSettings();
        }
        catch { }

        return new AppSettings();
    }

    public static void Save(AppSettings settings)
    {
        try
        {
            Directory.CreateDirectory(Folder);
            File.WriteAllText(FilePath, JsonSerializer.Serialize(settings, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch { }
    }

    public static void SetRunAtStartup(bool enabled)
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, writable: true);
            if (enabled)
            {
                var path = Environment.ProcessPath ?? string.Empty;
                key?.SetValue(RunValueName, $"\"{path}\"");
            }
            else
            {
                key?.DeleteValue(RunValueName, throwOnMissingValue: false);
            }
        }
        catch { }
    }

    public static void RemoveLegacyVdiStartup()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, writable: true);
            key?.DeleteValue("VDIToolkit", throwOnMissingValue: false);
        }
        catch { }
    }
}

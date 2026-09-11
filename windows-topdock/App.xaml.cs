using System.Windows;

namespace TopDock;

public partial class App : System.Windows.Application
{
    private Mutex? _singleInstanceMutex;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        if (e.Args.Contains("--content-test", StringComparer.OrdinalIgnoreCase))
        {
            ContentChecks.Run();
            Shutdown(0);
            return;
        }

        if (e.Args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
        {
            var windows = WindowService.GetWindows(IntPtr.Zero);
            Console.WriteLine($"TopDock self-test passed. Visible switchable windows: {windows.Count}");
            Shutdown(0);
            return;
        }

        if (e.Args.Contains("--paste-config-test", StringComparer.OrdinalIgnoreCase))
        {
            Console.WriteLine($"Host clipboard typing settings: {HostClipboardTyper.SettingsDescription}");
            Shutdown(0);
            return;
        }

        _singleInstanceMutex = new Mutex(initiallyOwned: true, "Local\\TopDock.SingleInstance", out var isFirstInstance);
        if (!isFirstInstance)
        {
            System.Windows.MessageBox.Show(
                "TopDock is already running in the notification area.\n\nPress Ctrl + Alt + Space to show it.",
                "TopDock", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            Shutdown(0);
            return;
        }

        var mainWindow = new MainWindow();
        MainWindow = mainWindow;
        mainWindow.Show();
    }
}

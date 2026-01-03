import SwiftUI
import AppKit

/// Haupteinstiegspunkt der App
@main
struct KonfliktSimulatorApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.automatic)
        .defaultSize(width: 1000, height: 700)
        .commands {
            // Menü-Befehle
            CommandGroup(replacing: .newItem) {
                Button("Neue Session") {
                    NotificationCenter.default.post(name: .newSession, object: nil)
                }
                .keyboardShortcut("n", modifiers: .command)
            }
        }

        Settings {
            SettingsView()
        }
    }
}

// Notification für Menü-Aktionen
extension Notification.Name {
    static let newSession = Notification.Name("newSession")
}

/// AppDelegate to handle activation for Swift Package executables
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Swift Package executables don't create proper app bundles
        // This ensures the app appears in the foreground with a window
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }
}

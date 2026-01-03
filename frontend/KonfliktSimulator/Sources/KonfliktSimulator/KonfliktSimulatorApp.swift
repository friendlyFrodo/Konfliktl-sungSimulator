import SwiftUI

/// Haupteinstiegspunkt der App
@main
struct KonfliktSimulatorApp: App {
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

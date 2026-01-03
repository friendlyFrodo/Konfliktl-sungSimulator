import SwiftUI

/// Settings View für App-Einstellungen
struct SettingsView: View {
    @AppStorage("serverURL") private var serverURL = "ws://localhost:8080/ws"
    @State private var testConnectionStatus: ConnectionStatus = .idle

    enum ConnectionStatus {
        case idle, testing, success, failed(String)
    }

    var body: some View {
        NavigationStack {
            Form {
                // Szenarien-Verwaltung
                Section("Szenarien") {
                    NavigationLink {
                        ScenarioManagerView()
                    } label: {
                        Label("Szenarien verwalten", systemImage: "doc.text.magnifyingglass")
                    }
                }

                Section("Server-Verbindung") {
                    TextField("WebSocket URL", text: $serverURL)
                        .textFieldStyle(.roundedBorder)

                    HStack {
                        Button("Verbindung testen") {
                            testConnection()
                        }

                        Spacer()

                        switch testConnectionStatus {
                        case .idle:
                            EmptyView()
                        case .testing:
                            ProgressView()
                                .scaleEffect(0.8)
                        case .success:
                            Label("Verbunden", systemImage: "checkmark.circle.fill")
                                .foregroundColor(.green)
                        case .failed(let error):
                            Label(error, systemImage: "xmark.circle.fill")
                                .foregroundColor(.red)
                                .font(.caption)
                        }
                    }
                }

                Section("Info") {
                    LabeledContent("Version", value: "0.2.0")
                    LabeledContent("Backend", value: "Python + LangGraph")
                    LabeledContent("LLM", value: "Claude (Anthropic)")
                }
            }
            .formStyle(.grouped)
            .frame(minWidth: 450, minHeight: 400)
            .navigationTitle("Einstellungen")
        }
    }

    private func testConnection() {
        testConnectionStatus = .testing

        guard let url = URL(string: serverURL.replacingOccurrences(of: "ws://", with: "http://").replacingOccurrences(of: "/ws", with: "/health")) else {
            testConnectionStatus = .failed("Invalid URL")
            return
        }

        Task {
            do {
                let (_, response) = try await URLSession.shared.data(from: url)
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode == 200 {
                    testConnectionStatus = .success
                } else {
                    testConnectionStatus = .failed("Server nicht erreichbar")
                }
            } catch {
                testConnectionStatus = .failed(error.localizedDescription)
            }
        }
    }
}

#Preview {
    SettingsView()
}

import SwiftUI

/// Haupt-Content-View der App
struct ContentView: View {
    @StateObject private var chatViewModel = ChatViewModel()

    // Session Configuration
    @State private var selectedMode: SimulationMode = .mediator
    @State private var agentAConfig = AgentConfig(
        name: "Maria",
        prompt: "Du bist Maria, 42 Jahre, Senior Projektmanagerin mit 15 Jahren Berufserfahrung. Du bist direkt, professionell und erwartest Respekt für deine Position. Du fühlst dich von Stefan hintergangen und bist enttäuscht über seinen Vertrauensbruch."
    )
    @State private var agentBConfig = AgentConfig(
        name: "Stefan",
        prompt: "Du bist Stefan, 35 Jahre, ambitionierter Projektmitarbeiter der Karriere machen will. Du bist ehrgeizig, manchmal ungeduldig und verstehst nicht, warum Maria so reagiert. Du wolltest Initiative zeigen und siehst dich zu Unrecht kritisiert."
    )
    @State private var scenarioText: String = """
Maria (42, Senior Projektmanagerin) und Stefan (35, ambitionierter Projektmitarbeiter) arbeiten seit 2 Jahren im selben Team. \
Letzte Woche hat Stefan dem Abteilungsleiter eine innovative Lösung für das aktuelle Kundenprojekt präsentiert - ohne Maria vorher einzuweihen. \
Die Idee wurde gut aufgenommen, und der Chef lobte Stefan öffentlich. Maria fühlt sich übergangen und hinterfragt Stefans Loyalität. \
Stefan versteht nicht, warum Maria so reagiert - er wollte doch nur Initiative zeigen. Beide treffen sich jetzt zum Klärungsgespräch.
"""
    @State private var userRole: String = "agent_a"

    // UI State
    @State private var showingNewSessionSheet = true
    @State private var showingSettings = false

    var body: some View {
        NavigationSplitView {
            // Sidebar
            SidebarView(
                isConnected: chatViewModel.webSocketService.isConnected,
                onNewSession: { showingNewSessionSheet = true },
                onSettings: { showingSettings = true }
            )
            .frame(minWidth: 200)
        } detail: {
            // Main Content
            if chatViewModel.isSessionActive || !chatViewModel.messages.isEmpty {
                ChatView(viewModel: chatViewModel)
            } else {
                WelcomeView(onStart: { showingNewSessionSheet = true })
            }
        }
        .sheet(isPresented: $showingNewSessionSheet) {
            NewSessionSheet(
                mode: $selectedMode,
                agentAConfig: $agentAConfig,
                agentBConfig: $agentBConfig,
                scenarioText: $scenarioText,
                userRole: $userRole,
                onStart: startNewSession,
                onCancel: { showingNewSessionSheet = false }
            )
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView()
        }
        .onAppear {
            chatViewModel.connect()
        }
        .onDisappear {
            chatViewModel.disconnect()
        }
        .alert("Fehler", isPresented: .init(
            get: { chatViewModel.errorMessage != nil },
            set: { if !$0 { chatViewModel.errorMessage = nil } }
        )) {
            Button("OK") {
                chatViewModel.errorMessage = nil
            }
        } message: {
            Text(chatViewModel.errorMessage ?? "")
        }
    }

    private func startNewSession() {
        showingNewSessionSheet = false
        chatViewModel.startSession(
            mode: selectedMode,
            agentAConfig: agentAConfig,
            agentBConfig: agentBConfig,
            scenario: scenarioText.isEmpty ? nil : scenarioText,
            userRole: selectedMode == .participant ? userRole : nil
        )
    }

    private var webSocketService: WebSocketService {
        chatViewModel.webSocketService
    }
}

/// Sidebar
struct SidebarView: View {
    let isConnected: Bool
    let onNewSession: () -> Void
    let onSettings: () -> Void

    var body: some View {
        List {
            Section("Session") {
                Button(action: onNewSession) {
                    Label("Neue Session", systemImage: "plus.circle")
                }
            }

            Section("Status") {
                HStack {
                    Circle()
                        .fill(isConnected ? .green : .red)
                        .frame(width: 8, height: 8)
                    Text(isConnected ? "Verbunden" : "Getrennt")
                        .foregroundColor(.secondary)
                }
            }
        }
        .listStyle(.sidebar)
        .toolbar {
            ToolbarItem {
                Button(action: onSettings) {
                    Image(systemName: "gear")
                }
            }
        }
    }
}

/// Welcome Screen
struct WelcomeView: View {
    let onStart: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "bubble.left.and.bubble.right.fill")
                .font(.system(size: 64))
                .foregroundColor(.accentColor)

            Text("Konflikt-Simulator")
                .font(.largeTitle.bold())

            Text("Trainiere Konfliktlösung mit KI-gestützten Simulationen")
                .font(.title3)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button("Neue Session starten") {
                onStart()
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding(40)
    }
}

/// Sheet für neue Session
struct NewSessionSheet: View {
    @Binding var mode: SimulationMode
    @Binding var agentAConfig: AgentConfig
    @Binding var agentBConfig: AgentConfig
    @Binding var scenarioText: String
    @Binding var userRole: String

    let onStart: () -> Void
    let onCancel: () -> Void

    // Szenarien aus der Datenbank
    @StateObject private var scenarioService = ScenarioService.shared

    var body: some View {
        NavigationStack {
            Form {
                // Modus
                Section("Modus") {
                    Picker("Modus", selection: $mode) {
                        ForEach(SimulationMode.allCases, id: \.self) { mode in
                            Text(mode.displayName).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)

                    Text(mode.description)
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if mode == .participant {
                        Picker("Deine Rolle", selection: $userRole) {
                            Text(agentAConfig.name).tag("agent_a")
                            Text(agentBConfig.name).tag("agent_b")
                        }
                    }
                }

                // Szenario
                Section("Szenario") {
                    if scenarioService.isLoading {
                        ProgressView("Lade Szenarien...")
                    } else {
                        Menu("Szenario auswählen") {
                            ForEach(scenarioService.scenarios) { scenario in
                                Button {
                                    selectScenario(scenario)
                                } label: {
                                    HStack {
                                        Text(scenario.name)
                                        if scenario.isPreset {
                                            Text("(Preset)")
                                                .foregroundColor(.secondary)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    TextEditor(text: $scenarioText)
                        .frame(minHeight: 80)
                        .font(.body)
                }

                // Agenten
                Section("Agenten") {
                    AgentConfigPanel(
                        agentAConfig: $agentAConfig,
                        agentBConfig: $agentBConfig
                    )
                }
            }
            .formStyle(.grouped)
            .frame(minWidth: 500, minHeight: 600)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Starten", action: onStart)
                        .buttonStyle(.borderedProminent)
                }
            }
            .navigationTitle("Neue Session")
            .task {
                // Szenarien beim Öffnen laden
                await scenarioService.fetchScenarios()
                // Erstes Szenario automatisch auswählen falls vorhanden
                if let firstScenario = scenarioService.scenarios.first {
                    selectScenario(firstScenario)
                }
            }
        }
    }

    private func selectScenario(_ scenario: Scenario) {
        scenarioText = scenario.scenarioText
        agentAConfig = scenario.toAgentAConfig()
        agentBConfig = scenario.toAgentBConfig()
    }
}

#Preview {
    ContentView()
}

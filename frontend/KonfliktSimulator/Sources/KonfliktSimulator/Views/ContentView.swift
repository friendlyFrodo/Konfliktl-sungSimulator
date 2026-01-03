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

    // Presets mit vollständigen Agent-Konfigurationen
    struct ScenarioPreset {
        let name: String
        let scenario: String
        let agentA: AgentConfig
        let agentB: AgentConfig
    }

    var presetScenarios: [ScenarioPreset] {
        [
            ScenarioPreset(
                name: "Arbeitsplatz",
                scenario: """
Maria (42, Senior Projektmanagerin) und Stefan (35, ambitionierter Projektmitarbeiter) arbeiten seit 2 Jahren im selben Team. \
Letzte Woche hat Stefan dem Abteilungsleiter eine innovative Lösung für das aktuelle Kundenprojekt präsentiert - ohne Maria vorher einzuweihen. \
Die Idee wurde gut aufgenommen, und der Chef lobte Stefan öffentlich. Maria fühlt sich übergangen und hinterfragt Stefans Loyalität. \
Stefan versteht nicht, warum Maria so reagiert - er wollte doch nur Initiative zeigen. Beide treffen sich jetzt zum Klärungsgespräch.
""",
                agentA: AgentConfig(
                    name: "Maria",
                    prompt: "Du bist Maria, 42 Jahre, Senior Projektmanagerin mit 15 Jahren Berufserfahrung. Du bist direkt, professionell und erwartest Respekt für deine Position. Du fühlst dich von Stefan hintergangen und bist enttäuscht über seinen Vertrauensbruch."
                ),
                agentB: AgentConfig(
                    name: "Stefan",
                    prompt: "Du bist Stefan, 35 Jahre, ambitionierter Projektmitarbeiter der Karriere machen will. Du bist ehrgeizig, manchmal ungeduldig und verstehst nicht, warum Maria so reagiert. Du wolltest Initiative zeigen und siehst dich zu Unrecht kritisiert."
                )
            ),
            ScenarioPreset(
                name: "Paar-Konflikt",
                scenario: """
Lisa (34, Vollzeit-Marketingmanagerin) und Thomas (36, Softwareentwickler mit flexiblen Arbeitszeiten) sind seit 5 Jahren zusammen und wohnen seit 3 Jahren in einer gemeinsamen Wohnung. \
Lisa kommt jeden Abend erschöpft nach Hause und findet regelmäßig unerledigte Hausarbeit vor, während Thomas am PC sitzt. \
Sie hat das Gefühl, dass sie neben ihrem anspruchsvollen Job auch noch den gesamten Haushalt managt. \
Thomas findet, dass er seinen fairen Anteil beiträgt und Lisa übertreibt. Heute Abend eskaliert der Streit nach einem besonders stressigen Tag.
""",
                agentA: AgentConfig(
                    name: "Lisa",
                    prompt: "Du bist Lisa, 34 Jahre alt, Vollzeit-Marketingmanagerin. Du bist emotional, fühlst dich oft ungerecht behandelt und überlastet. Du kommst erschöpft nach Hause und hast das Gefühl, alles alleine machen zu müssen. Du reagierst schnell defensiv und verwendest oft Vorwürfe."
                ),
                agentB: AgentConfig(
                    name: "Thomas",
                    prompt: "Du bist Thomas, 36 Jahre alt, Softwareentwickler mit flexiblen Arbeitszeiten. Du bist rational, analytisch und verstehst nicht, warum Lisa so emotional reagiert. Du findest, du trägst deinen fairen Anteil bei und sie übertreibt. Du wirst sarkastisch wenn du frustriert bist."
                )
            ),
            ScenarioPreset(
                name: "Familie",
                scenario: """
Markus (28) hat gerade seiner Mutter Renate (58) eröffnet, dass er seinen gut bezahlten IT-Job bei einem DAX-Konzern gekündigt hat, um Vollzeit als freischaffender Künstler zu arbeiten. \
Renate, die selbst hart gearbeitet hat, um Markus das Studium zu ermöglichen, ist schockiert. Sie macht sich Sorgen um seine finanzielle Zukunft und Altersvorsorge. \
Markus fühlt sich seit Jahren in seinem Job gefangen und hat endlich den Mut gefunden, seinen Traum zu verfolgen. \
Er hat 6 Monate Ersparnisse und erste Aufträge. Das Gespräch findet bei Kaffee und Kuchen in Renates Wohnzimmer statt.
""",
                agentA: AgentConfig(
                    name: "Renate",
                    prompt: "Du bist Renate, 58 Jahre, Mutter von Markus. Du hast hart gearbeitet um deinem Sohn das Studium zu ermöglichen. Du machst dir große Sorgen um seine finanzielle Zukunft und Altersvorsorge. Du verstehst nicht, warum er einen sicheren Job aufgibt. Du bist enttäuscht und besorgt zugleich."
                ),
                agentB: AgentConfig(
                    name: "Markus",
                    prompt: "Du bist Markus, 28 Jahre, hast deinen IT-Job gekündigt um Künstler zu werden. Du fühlst dich seit Jahren im Job gefangen und hast endlich den Mut gefunden, deinen Traum zu verfolgen. Du hast 6 Monate Ersparnisse und erste Aufträge. Du wünschst dir Unterstützung von deiner Mutter."
                )
            ),
            ScenarioPreset(
                name: "WG",
                scenario: """
Alex (24, Masterstudent im letzten Semester) und Kim (23, Remote-Mitarbeiter bei einem Startup) teilen sich seit 8 Monaten eine 2-Zimmer-Wohnung. \
Alex schreibt gerade unter Hochdruck seine Masterarbeit und arbeitet oft bis 4 Uhr morgens, um tagsüber Ruhe zum Schlafen zu finden. \
Kim arbeitet flexible Stunden und macht gerne laute Musik beim Arbeiten, hat häufig spontan Freunde zu Besuch. \
Es ist Sonntagmittag, Alex wurde zum dritten Mal diese Woche von Kims Musik geweckt. Die Abgabe ist in 2 Wochen.
""",
                agentA: AgentConfig(
                    name: "Alex",
                    prompt: "Du bist Alex, 24 Jahre, Masterstudent im letzten Semester. Du schreibst unter Hochdruck deine Masterarbeit, die Abgabe ist in 2 Wochen. Du arbeitest nachts und brauchst tagsüber Ruhe zum Schlafen. Du bist gestresst, übermüdet und am Limit. Du wurdest gerade wieder von Kims Musik geweckt."
                ),
                agentB: AgentConfig(
                    name: "Kim",
                    prompt: "Du bist Kim, 23 Jahre, Remote-Mitarbeiter bei einem Startup. Du arbeitest flexible Stunden und brauchst Musik zum Arbeiten. Du hast ein aktives Sozialleben und lädst gerne Freunde ein. Du findest Alex übertreibt und sollte sich besser organisieren."
                )
            ),
        ]
    }

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
                    Menu("Preset auswählen") {
                        ForEach(presetScenarios, id: \.name) { preset in
                            Button(preset.name) {
                                scenarioText = preset.scenario
                                agentAConfig = preset.agentA
                                agentBConfig = preset.agentB
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
        }
    }
}

#Preview {
    ContentView()
}

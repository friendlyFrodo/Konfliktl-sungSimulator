import SwiftUI

/// View zur Verwaltung von Szenarien (Erstellen, Bearbeiten, Löschen)
struct ScenarioManagerView: View {
    @StateObject private var scenarioService = ScenarioService.shared
    @State private var showingCreateSheet = false
    @State private var scenarioToEdit: Scenario?
    @State private var showingDeleteConfirmation = false
    @State private var scenarioToDelete: Scenario?

    var body: some View {
        List {
            // Presets Section
            Section("Voreinstellungen") {
                ForEach(scenarioService.scenarios.filter { $0.isPreset }) { scenario in
                    ScenarioRow(scenario: scenario, isPreset: true) {
                        // Presets können nicht bearbeitet werden
                    } onDelete: {
                        // Presets können nicht gelöscht werden
                    }
                }
            }

            // Custom Scenarios Section
            Section("Eigene Szenarien") {
                if scenarioService.scenarios.filter({ !$0.isPreset }).isEmpty {
                    Text("Noch keine eigenen Szenarien erstellt")
                        .foregroundColor(.secondary)
                        .italic()
                } else {
                    ForEach(scenarioService.scenarios.filter { !$0.isPreset }) { scenario in
                        ScenarioRow(scenario: scenario, isPreset: false) {
                            scenarioToEdit = scenario
                        } onDelete: {
                            scenarioToDelete = scenario
                            showingDeleteConfirmation = true
                        }
                    }
                }
            }
        }
        .navigationTitle("Szenarien verwalten")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingCreateSheet = true
                } label: {
                    Label("Neues Szenario", systemImage: "plus")
                }
            }

            ToolbarItem(placement: .automatic) {
                Button {
                    Task {
                        await scenarioService.fetchScenarios()
                    }
                } label: {
                    Label("Aktualisieren", systemImage: "arrow.clockwise")
                }
            }
        }
        .sheet(isPresented: $showingCreateSheet) {
            ScenarioEditorSheet(
                mode: .create,
                onSave: { create in
                    Task {
                        _ = await scenarioService.createScenario(create)
                    }
                }
            )
        }
        .sheet(item: $scenarioToEdit) { scenario in
            ScenarioEditorSheet(
                mode: .edit(scenario),
                onSave: { update in
                    Task {
                        _ = await scenarioService.updateScenario(
                            scenario.id,
                            update: ScenarioUpdate(
                                name: update.name,
                                scenarioText: update.scenarioText,
                                agentAName: update.agentAName,
                                agentAPrompt: update.agentAPrompt,
                                agentBName: update.agentBName,
                                agentBPrompt: update.agentBPrompt
                            )
                        )
                    }
                }
            )
        }
        .alert("Szenario löschen?", isPresented: $showingDeleteConfirmation) {
            Button("Abbrechen", role: .cancel) {
                scenarioToDelete = nil
            }
            Button("Löschen", role: .destructive) {
                if let scenario = scenarioToDelete {
                    Task {
                        _ = await scenarioService.deleteScenario(scenario.id)
                    }
                }
                scenarioToDelete = nil
            }
        } message: {
            if let scenario = scenarioToDelete {
                Text("Möchtest du \"\(scenario.name)\" wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.")
            }
        }
        .task {
            await scenarioService.fetchScenarios()
        }
    }
}

/// Zeile für ein Szenario in der Liste
struct ScenarioRow: View {
    let scenario: Scenario
    let isPreset: Bool
    let onEdit: () -> Void
    let onDelete: () -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(scenario.name)
                        .font(.headline)
                    if isPreset {
                        Text("Preset")
                            .font(.caption)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.blue.opacity(0.2))
                            .foregroundColor(.blue)
                            .cornerRadius(4)
                    }
                }

                Text("\(scenario.agentAName) vs. \(scenario.agentBName)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Text(scenario.scenarioText.prefix(100) + (scenario.scenarioText.count > 100 ? "..." : ""))
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }

            Spacer()

            if !isPreset {
                HStack(spacing: 8) {
                    Button {
                        onEdit()
                    } label: {
                        Image(systemName: "pencil")
                    }
                    .buttonStyle(.borderless)

                    Button {
                        onDelete()
                    } label: {
                        Image(systemName: "trash")
                            .foregroundColor(.red)
                    }
                    .buttonStyle(.borderless)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

/// Editor für Szenarien (Erstellen/Bearbeiten)
struct ScenarioEditorSheet: View {
    enum Mode {
        case create
        case edit(Scenario)

        var title: String {
            switch self {
            case .create: return "Neues Szenario"
            case .edit: return "Szenario bearbeiten"
            }
        }
    }

    let mode: Mode
    let onSave: (ScenarioCreate) -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var name: String = ""
    @State private var scenarioText: String = ""
    @State private var agentAName: String = ""
    @State private var agentAPrompt: String = ""
    @State private var agentBName: String = ""
    @State private var agentBPrompt: String = ""

    var isValid: Bool {
        !name.isEmpty &&
        !scenarioText.isEmpty &&
        !agentAName.isEmpty &&
        !agentAPrompt.isEmpty &&
        !agentBName.isEmpty &&
        !agentBPrompt.isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Allgemein") {
                    TextField("Name", text: $name)
                        .textFieldStyle(.roundedBorder)
                }

                Section("Szenario-Beschreibung") {
                    TextEditor(text: $scenarioText)
                        .frame(minHeight: 100)
                }

                Section("Agent A") {
                    TextField("Name", text: $agentAName)
                        .textFieldStyle(.roundedBorder)
                    TextEditor(text: $agentAPrompt)
                        .frame(minHeight: 80)
                }

                Section("Agent B") {
                    TextField("Name", text: $agentBName)
                        .textFieldStyle(.roundedBorder)
                    TextEditor(text: $agentBPrompt)
                        .frame(minHeight: 80)
                }
            }
            .formStyle(.grouped)
            .frame(minWidth: 500, minHeight: 600)
            .navigationTitle(mode.title)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Speichern") {
                        let create = ScenarioCreate(
                            name: name,
                            scenarioText: scenarioText,
                            agentAName: agentAName,
                            agentAPrompt: agentAPrompt,
                            agentBName: agentBName,
                            agentBPrompt: agentBPrompt
                        )
                        onSave(create)
                        dismiss()
                    }
                    .disabled(!isValid)
                    .buttonStyle(.borderedProminent)
                }
            }
            .onAppear {
                // Bei Bearbeiten: Felder mit vorhandenen Daten füllen
                if case .edit(let scenario) = mode {
                    name = scenario.name
                    scenarioText = scenario.scenarioText
                    agentAName = scenario.agentAName
                    agentAPrompt = scenario.agentAPrompt
                    agentBName = scenario.agentBName
                    agentBPrompt = scenario.agentBPrompt
                }
            }
        }
    }
}

#Preview {
    NavigationStack {
        ScenarioManagerView()
    }
}

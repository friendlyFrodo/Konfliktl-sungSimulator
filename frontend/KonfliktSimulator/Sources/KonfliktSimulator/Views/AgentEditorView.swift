import SwiftUI

/// Editor für Agenten-Konfigurationen
struct AgentEditorView: View {
    @Binding var agentConfig: AgentConfig
    let title: String
    let accentColor: Color

    @State private var isExpanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Circle()
                    .fill(accentColor)
                    .frame(width: 24, height: 24)
                    .overlay(
                        Text(String(agentConfig.name.prefix(1)))
                            .font(.caption.bold())
                            .foregroundColor(.white)
                    )

                Text(title)
                    .font(.headline)

                Spacer()

                Button(action: { withAnimation { isExpanded.toggle() } }) {
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Name Input
            HStack {
                Text("Name:")
                    .foregroundColor(.secondary)
                TextField("Name", text: $agentConfig.name)
                    .textFieldStyle(.roundedBorder)
            }

            // Expanded: Prompt Editor
            if isExpanded {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Persönlichkeits-Prompt:")
                        .foregroundColor(.secondary)
                        .font(.caption)

                    TextEditor(text: $agentConfig.prompt)
                        .font(.system(.body, design: .monospaced))
                        .frame(minHeight: 150)
                        .padding(4)
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(8)
                }
            }
        }
        .padding()
        .background(accentColor.opacity(0.05))
        .cornerRadius(12)
    }
}

/// Panel zum Auswählen und Konfigurieren von Agenten
struct AgentConfigPanel: View {
    @Binding var agentAConfig: AgentConfig
    @Binding var agentBConfig: AgentConfig

    var body: some View {
        VStack(spacing: 16) {
            AgentEditorView(
                agentConfig: $agentAConfig,
                title: "Agent A",
                accentColor: .pink
            )

            AgentEditorView(
                agentConfig: $agentBConfig,
                title: "Agent B",
                accentColor: .blue
            )
        }
    }
}

#Preview {
    struct PreviewWrapper: View {
        @State var configA = AgentConfig.defaultAgentA
        @State var configB = AgentConfig.defaultAgentB

        var body: some View {
            AgentConfigPanel(agentAConfig: $configA, agentBConfig: $configB)
                .padding()
                .frame(width: 400)
        }
    }

    return PreviewWrapper()
}

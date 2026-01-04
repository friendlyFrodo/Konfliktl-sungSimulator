import SwiftUI

/// Zeigt eine Experten-Analyse für eine Nachricht an
struct AnalysisView: View {
    let message: Message
    let analysis: String?
    let isLoading: Bool
    let onRequestAnalysis: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Image(systemName: "sparkles")
                    .foregroundColor(.yellow)
                Text(headerTitle)
                    .font(.headline)
                Spacer()
            }

            Divider()

            if isLoading {
                // Loading State
                VStack(spacing: 12) {
                    ProgressView()
                        .scaleEffect(1.2)
                    Text("Analysiere...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
            } else if let analysis = analysis {
                // Analysis Content
                ScrollView {
                    Text(analysis)
                        .font(.body)
                        .textSelection(.enabled)
                        .lineSpacing(4)
                }
            } else {
                // Not yet loaded
                VStack(spacing: 12) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 40))
                        .foregroundColor(.secondary.opacity(0.5))

                    Text("Klicke um eine Experten-Analyse zu erhalten")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)

                    Button(action: onRequestAnalysis) {
                        HStack {
                            Image(systemName: "wand.and.stars")
                            Text("Analysieren")
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.accentColor)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
            }
        }
        .padding()
        .frame(minWidth: 400, maxWidth: 500, minHeight: 200, maxHeight: 500)
    }

    private var headerTitle: String {
        switch message.agent {
        case .agentA, .agentB:
            return "Experten-Analyse: \(message.agentName)"
        case .user, .mediator:
            return "Coach-Feedback: Mediator"
        case .evaluator:
            return "Info"
        }
    }
}

/// Button für Experten-Analyse in der MessageBubble
struct AnalysisButton: View {
    let message: Message
    let hasAnalysis: Bool
    let isLoading: Bool
    @Binding var showingAnalysis: Bool

    var body: some View {
        Button(action: { showingAnalysis.toggle() }) {
            ZStack {
                if isLoading {
                    ProgressView()
                        .scaleEffect(0.6)
                } else {
                    Image(systemName: hasAnalysis ? "sparkles" : "sparkle")
                        .font(.system(size: 14))
                        .foregroundColor(hasAnalysis ? .yellow : .secondary.opacity(0.6))
                }
            }
            .frame(width: 24, height: 24)
        }
        .buttonStyle(.plain)
        .help(hasAnalysis ? "Analyse anzeigen" : "Experten-Analyse anfordern")
    }
}

#Preview {
    AnalysisView(
        message: Message(
            agent: .agentA,
            agentName: "Lisa",
            content: "Das stimmt doch gar nicht!"
        ),
        analysis: """
        ## Was wird gesagt (Oberflächenebene)
        Lisa bestreitet eine Aussage von Thomas mit einer generellen Ablehnung.

        ## Was wird NICHT gesagt (Tiefenebene)
        - Konkrete Begründung für ihre Position
        - Welcher Teil genau nicht stimmt
        - Eigene Gefühle zu dem Thema

        ## Kommunikationsmuster
        - Defensive Reaktion
        - Generalisierung ("gar nicht")

        ## Hinweise für den Mediator
        - Nachfragen: "Was genau stimmt aus deiner Sicht nicht?"
        - Gefühle erkunden: "Wie fühlst du dich, wenn Thomas das sagt?"
        """,
        isLoading: false,
        onRequestAnalysis: {}
    )
}

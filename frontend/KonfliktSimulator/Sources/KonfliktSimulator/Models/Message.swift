import Foundation

/// Eine Nachricht in der Konversation
struct Message: Identifiable, Codable, Equatable {
    let id: UUID
    let agent: Agent
    let agentName: String
    let content: String
    let timestamp: Date
    var isStreaming: Bool

    init(
        id: UUID = UUID(),
        agent: Agent,
        agentName: String,
        content: String,
        timestamp: Date = Date(),
        isStreaming: Bool = false
    ) {
        self.id = id
        self.agent = agent
        self.agentName = agentName
        self.content = content
        self.timestamp = timestamp
        self.isStreaming = isStreaming
    }

    /// Erstellt eine Message aus einer Server-Response
    static func fromServerMessage(_ serverMsg: ServerMessage) -> Message? {
        switch serverMsg {
        case .agentMessage(let msg):
            return Message(
                agent: msg.agent == "a" ? .agentA : (msg.agent == "b" ? .agentB : .evaluator),
                agentName: msg.agentName,
                content: msg.content,
                timestamp: msg.timestamp
            )
        case .evaluation(let eval):
            return Message(
                agent: .evaluator,
                agentName: "Coach",
                content: eval.content,
                timestamp: Date()
            )
        default:
            return nil
        }
    }
}

/// Die verschiedenen Agenten/Rollen
enum Agent: String, Codable, CaseIterable {
    case agentA = "a"
    case agentB = "b"
    case mediator = "mediator"
    case evaluator = "evaluator"
    case user = "user"
}

/// Simulationsmodus
enum SimulationMode: String, Codable, CaseIterable {
    case mediator = "mediator"
    case participant = "participant"

    var displayName: String {
        switch self {
        case .mediator: return "Mediator"
        case .participant: return "Teilnehmer"
        }
    }

    var description: String {
        switch self {
        case .mediator: return "Beobachte den Konflikt und greife als Coach ein"
        case .participant: return "Übernimm eine der Rollen im Konflikt"
        }
    }
}

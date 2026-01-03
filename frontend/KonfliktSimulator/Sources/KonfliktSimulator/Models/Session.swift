import Foundation

/// Eine Simulations-Session
struct Session: Identifiable, Codable {
    let id: String
    let mode: SimulationMode
    let agentAConfig: AgentConfig
    let agentBConfig: AgentConfig
    var messages: [Message]
    let createdAt: Date
    var turns: Int

    init(
        id: String,
        mode: SimulationMode,
        agentAConfig: AgentConfig,
        agentBConfig: AgentConfig,
        messages: [Message] = [],
        createdAt: Date = Date(),
        turns: Int = 0
    ) {
        self.id = id
        self.mode = mode
        self.agentAConfig = agentAConfig
        self.agentBConfig = agentBConfig
        self.messages = messages
        self.createdAt = createdAt
        self.turns = turns
    }
}

// MARK: - Server Messages (WebSocket Protocol)

/// Nachrichten vom Client zum Server
enum ClientMessage: Codable {
    case startSession(StartSessionRequest)
    case userMessage(UserMessageRequest)
    case continueSession(ContinueRequest)
    case stop(StopRequest)
    case requestEvaluation(EvaluationRequest)

    struct StartSessionRequest: Codable {
        let type = "start_session"
        let mode: String
        let agentAConfig: AgentConfigRequest
        let agentBConfig: AgentConfigRequest
        let scenario: String?
        let userRole: String?

        enum CodingKeys: String, CodingKey {
            case type
            case mode
            case agentAConfig = "agent_a_config"
            case agentBConfig = "agent_b_config"
            case scenario
            case userRole = "user_role"
        }
    }

    struct AgentConfigRequest: Codable {
        let name: String
        let prompt: String
    }

    struct UserMessageRequest: Codable {
        let type = "user_message"
        let sessionId: String
        let content: String
        let role: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
            case content
            case role
        }
    }

    struct ContinueRequest: Codable {
        let type = "continue"
        let sessionId: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
        }
    }

    struct StopRequest: Codable {
        let type = "stop"
        let sessionId: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
        }
    }

    struct EvaluationRequest: Codable {
        let type = "request_evaluation"
        let sessionId: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
        }
    }
}

/// Nachrichten vom Server zum Client
enum ServerMessage: Decodable {
    case sessionStarted(SessionStartedResponse)
    case agentMessage(AgentMessageResponse)
    case streamingChunk(StreamingChunkResponse)
    case typing(TypingResponse)
    case waitingForInput(WaitingForInputResponse)
    case evaluation(EvaluationResponse)
    case error(ErrorResponse)

    struct SessionStartedResponse: Decodable {
        let type: String
        let sessionId: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
        }
    }

    struct AgentMessageResponse: Decodable {
        let type: String
        let sessionId: String
        let agent: String
        let agentName: String
        let content: String
        let timestamp: Date

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
            case agent
            case agentName = "agent_name"
            case content
            case timestamp
        }
    }

    struct StreamingChunkResponse: Decodable {
        let type: String
        let sessionId: String
        let agent: String
        let agentName: String
        let chunk: String
        let isFinal: Bool

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
            case agent
            case agentName = "agent_name"
            case chunk
            case isFinal = "is_final"
        }
    }

    struct TypingResponse: Decodable {
        let type: String
        let sessionId: String
        let agent: String
        let agentName: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
            case agent
            case agentName = "agent_name"
        }
    }

    struct WaitingForInputResponse: Decodable {
        let type: String
        let sessionId: String
        let expectedRole: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
            case expectedRole = "expected_role"
        }
    }

    struct EvaluationResponse: Decodable {
        let type: String
        let sessionId: String
        let content: String

        enum CodingKeys: String, CodingKey {
            case type
            case sessionId = "session_id"
            case content
        }
    }

    struct ErrorResponse: Decodable {
        let type: String
        let message: String
    }

    enum CodingKeys: String, CodingKey {
        case type
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)

        let singleContainer = try decoder.singleValueContainer()

        switch type {
        case "session_started":
            self = .sessionStarted(try singleContainer.decode(SessionStartedResponse.self))
        case "agent_message":
            self = .agentMessage(try singleContainer.decode(AgentMessageResponse.self))
        case "streaming_chunk":
            self = .streamingChunk(try singleContainer.decode(StreamingChunkResponse.self))
        case "typing":
            self = .typing(try singleContainer.decode(TypingResponse.self))
        case "waiting_for_input":
            self = .waitingForInput(try singleContainer.decode(WaitingForInputResponse.self))
        case "evaluation":
            self = .evaluation(try singleContainer.decode(EvaluationResponse.self))
        case "error":
            self = .error(try singleContainer.decode(ErrorResponse.self))
        default:
            throw DecodingError.dataCorruptedError(
                forKey: .type,
                in: container,
                debugDescription: "Unknown message type: \(type)"
            )
        }
    }
}

import Foundation
import Combine

/// ViewModel für die Chat-Ansicht
@MainActor
class ChatViewModel: ObservableObject {
    // MARK: - Published Properties

    @Published var messages: [Message] = []
    @Published var inputText: String = ""
    @Published var isWaitingForInput: Bool = false
    @Published var expectedRole: String = "mediator"
    @Published var typingAgent: String? = nil
    @Published var typingAgentName: String? = nil
    @Published var currentSessionId: String? = nil
    @Published var isSessionActive: Bool = false
    @Published var errorMessage: String? = nil

    // Streaming
    @Published var streamingMessage: Message? = nil

    // Neue Architektur: User-Entscheidung nach jedem Statement
    @Published var isWaitingForDecision: Bool = false
    @Published var suggestedNextAgent: String? = nil   // "agent_a" oder "agent_b"
    @Published var suggestedNextName: String? = nil
    @Published var agentAName: String = "Agent A"
    @Published var agentBName: String = "Agent B"

    // MARK: - Services

    let webSocketService: WebSocketService
    private var cancellables = Set<AnyCancellable>()

    // Session Config
    private var currentMode: SimulationMode = .mediator
    private var currentAgentAConfig: AgentConfig = .defaultAgentA
    private var currentAgentBConfig: AgentConfig = .defaultAgentB
    private var currentUserRole: String? = nil

    // MARK: - Initialization

    init() {
        self.webSocketService = WebSocketService()
        setupMessageHandler()
        setupBindings()
    }

    // MARK: - Public Methods

    /// Verbindung herstellen
    func connect() {
        webSocketService.connect()
    }

    /// Verbindung trennen
    func disconnect() {
        webSocketService.disconnect()
    }

    /// Neue Session starten
    func startSession(
        mode: SimulationMode,
        agentAConfig: AgentConfig,
        agentBConfig: AgentConfig,
        scenario: String? = nil,
        userRole: String? = nil
    ) {
        // Reset
        messages = []
        streamingMessage = nil
        errorMessage = nil

        // Config speichern
        currentMode = mode
        currentAgentAConfig = agentAConfig
        currentAgentBConfig = agentBConfig
        currentUserRole = userRole

        // Session starten
        webSocketService.startSession(
            mode: mode,
            agentAConfig: agentAConfig,
            agentBConfig: agentBConfig,
            scenario: scenario,
            userRole: userRole
        )
    }

    /// Nachricht senden
    func sendMessage() {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              let sessionId = currentSessionId else {
            return
        }

        let content = inputText
        inputText = ""
        isWaitingForInput = false

        // User-Nachricht zur Liste hinzufügen
        let userMessage = Message(
            agent: .user,
            agentName: expectedRole == "mediator" ? "Mediator" : (currentUserRole == "agent_a" ? currentAgentAConfig.name : currentAgentBConfig.name),
            content: content
        )
        messages.append(userMessage)

        // An Server senden
        webSocketService.sendUserMessage(
            sessionId: sessionId,
            content: content,
            role: expectedRole
        )
    }

    /// Session stoppen und Evaluierung anfordern
    func stopAndEvaluate() {
        guard let sessionId = currentSessionId else { return }
        webSocketService.stopSession(sessionId: sessionId)
    }

    /// In die Situation eingreifen (unterbricht Streaming sofort)
    func intervene() {
        guard let sessionId = currentSessionId else { return }
        // Streaming sofort stoppen
        streamingMessage = nil
        typingAgent = nil
        typingAgentName = nil
        webSocketService.interruptSession(sessionId: sessionId)
    }

    /// Session fortsetzen (lässt den nächsten Agent sprechen)
    func continueSession() {
        guard let sessionId = currentSessionId else { return }
        isWaitingForInput = false
        isWaitingForDecision = false
        webSocketService.continueSession(sessionId: sessionId)
    }

    /// User entscheidet: Lass den anderen Agent antworten
    func letNextAgentSpeak() {
        continueSession()
    }

    /// User entscheidet: Selbst etwas beitragen
    func userWantsToContribute() {
        isWaitingForDecision = false
        isWaitingForInput = true
        expectedRole = "mediator"
    }

    /// Gespräch beenden und Evaluierung anfordern
    func requestEvaluation() {
        guard let sessionId = currentSessionId else { return }
        isWaitingForDecision = false
        isWaitingForInput = false
        webSocketService.stopSession(sessionId: sessionId)
    }

    // MARK: - Private Methods

    private func setupMessageHandler() {
        webSocketService.onMessage { [weak self] message in
            Task { @MainActor in
                self?.handleServerMessage(message)
            }
        }
    }

    private func setupBindings() {
        webSocketService.$connectionError
            .compactMap { $0 }
            .sink { [weak self] error in
                self?.errorMessage = error
            }
            .store(in: &cancellables)
    }

    private func handleServerMessage(_ message: ServerMessage) {
        switch message {
        case .sessionStarted(let response):
            currentSessionId = response.sessionId
            isSessionActive = true

        case .typing(let response):
            typingAgent = response.agent
            typingAgentName = response.agentName

            // Streaming-Message vorbereiten
            let agent: Agent = response.agent == "a" ? .agentA : (response.agent == "b" ? .agentB : .evaluator)
            streamingMessage = Message(
                agent: agent,
                agentName: response.agentName,
                content: "",
                isStreaming: true
            )

        case .streamingChunk(let response):
            // Content zum Streaming-Message hinzufügen
            if var streaming = streamingMessage {
                streaming = Message(
                    id: streaming.id,
                    agent: streaming.agent,
                    agentName: streaming.agentName,
                    content: streaming.content + response.chunk,
                    timestamp: streaming.timestamp,
                    isStreaming: !response.isFinal
                )
                streamingMessage = streaming
            }

        case .agentMessage(let response):
            // Typing beenden
            typingAgent = nil
            typingAgentName = nil

            // Finale Nachricht hinzufügen
            let agent: Agent = response.agent == "a" ? .agentA : (response.agent == "b" ? .agentB : .evaluator)
            let finalMessage = Message(
                agent: agent,
                agentName: response.agentName,
                content: response.content,
                timestamp: response.timestamp,
                isStreaming: false
            )
            messages.append(finalMessage)
            streamingMessage = nil
            print("📨 Added message from \(response.agentName), total messages: \(messages.count)")

        case .waitingForInput(let response):
            isWaitingForInput = true
            expectedRole = response.expectedRole
            typingAgent = nil
            typingAgentName = nil

        case .waitingForDecision(let response):
            // Neue Architektur: User entscheidet nach jedem Statement
            isWaitingForDecision = true
            isWaitingForInput = false
            suggestedNextAgent = response.suggestedNext
            suggestedNextName = response.suggestedNextName
            agentAName = response.agentAName
            agentBName = response.agentBName
            typingAgent = nil
            typingAgentName = nil
            streamingMessage = nil
            print("🎯 Waiting for decision - suggested: \(response.suggestedNextName)")

        case .evaluation(let response):
            typingAgent = nil
            typingAgentName = nil
            streamingMessage = nil

            let evalMessage = Message(
                agent: .evaluator,
                agentName: "Coach",
                content: response.content,
                isStreaming: false
            )
            messages.append(evalMessage)
            isSessionActive = false

        case .interrupted(let response):
            // User hat eingegriffen - Streaming/Typing stoppen
            streamingMessage = nil
            typingAgent = nil
            typingAgentName = nil
            isWaitingForInput = true
            expectedRole = "mediator"
            print("🛑 Session unterbrochen: \(response.message)")

        case .error(let response):
            errorMessage = response.message
            typingAgent = nil
            typingAgentName = nil
        }
    }
}

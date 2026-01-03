import Foundation
import Combine

/// WebSocket Service für Echtzeit-Kommunikation mit dem Backend
@MainActor
class WebSocketService: NSObject, ObservableObject {
    // MARK: - Published Properties

    @Published var isConnected = false
    @Published var connectionError: String?

    // MARK: - Private Properties

    private var webSocketTask: URLSessionWebSocketTask?
    private var urlSession: URLSession!
    private let serverURL: URL

    private var messageHandler: ((ServerMessage) -> Void)?
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 5

    // JSON Decoder mit ISO8601 Datum
    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    // JSON Encoder
    private let encoder = JSONEncoder()

    // MARK: - Initialization

    init(serverURL: URL = URL(string: "ws://localhost:8000/ws")!) {
        self.serverURL = serverURL
        super.init()
        self.urlSession = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
    }

    // MARK: - Public Methods

    /// Verbindung zum Server herstellen
    func connect() {
        guard webSocketTask == nil else { return }

        webSocketTask = urlSession.webSocketTask(with: serverURL)
        webSocketTask?.resume()

        isConnected = true
        connectionError = nil
        reconnectAttempts = 0

        receiveMessage()
    }

    /// Verbindung trennen
    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        isConnected = false
    }

    /// Message Handler setzen
    func onMessage(_ handler: @escaping (ServerMessage) -> Void) {
        self.messageHandler = handler
    }

    /// Neue Session starten
    func startSession(
        mode: SimulationMode,
        agentAConfig: AgentConfig,
        agentBConfig: AgentConfig,
        scenario: String? = nil,
        userRole: String? = nil
    ) {
        let request = ClientMessage.StartSessionRequest(
            mode: mode.rawValue,
            agentAConfig: .init(name: agentAConfig.name, prompt: agentAConfig.prompt),
            agentBConfig: .init(name: agentBConfig.name, prompt: agentBConfig.prompt),
            scenario: scenario,
            userRole: userRole
        )

        sendJSON(request)
    }

    /// User-Nachricht senden
    func sendUserMessage(sessionId: String, content: String, role: String) {
        let request = ClientMessage.UserMessageRequest(
            sessionId: sessionId,
            content: content,
            role: role
        )

        sendJSON(request)
    }

    /// Session fortsetzen
    func continueSession(sessionId: String) {
        let request = ClientMessage.ContinueRequest(sessionId: sessionId)
        sendJSON(request)
    }

    /// Session stoppen
    func stopSession(sessionId: String) {
        let request = ClientMessage.StopRequest(sessionId: sessionId)
        sendJSON(request)
    }

    /// Evaluierung anfordern
    func requestEvaluation(sessionId: String) {
        let request = ClientMessage.EvaluationRequest(sessionId: sessionId)
        sendJSON(request)
    }

    // MARK: - Private Methods

    private func sendJSON<T: Encodable>(_ object: T) {
        guard let webSocketTask = webSocketTask else {
            connectionError = "Not connected"
            return
        }

        do {
            let data = try encoder.encode(object)
            let message = URLSessionWebSocketTask.Message.data(data)
            webSocketTask.send(message) { [weak self] error in
                if let error = error {
                    Task { @MainActor in
                        self?.connectionError = error.localizedDescription
                    }
                }
            }
        } catch {
            connectionError = "Encoding error: \(error.localizedDescription)"
        }
    }

    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }

            switch result {
            case .success(let message):
                self.handleMessage(message)
                self.receiveMessage() // Continue receiving

            case .failure(let error):
                Task { @MainActor in
                    self.handleError(error)
                }
            }
        }
    }

    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        let data: Data

        switch message {
        case .string(let text):
            data = Data(text.utf8)
        case .data(let d):
            data = d
        @unknown default:
            return
        }

        do {
            let serverMessage = try decoder.decode(ServerMessage.self, from: data)
            Task { @MainActor in
                self.messageHandler?(serverMessage)
            }
        } catch {
            print("Decoding error: \(error)")
            // Try to extract error message from raw JSON
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let errorMsg = json["message"] as? String {
                Task { @MainActor in
                    self.connectionError = errorMsg
                }
            }
        }
    }

    private func handleError(_ error: Error) {
        isConnected = false
        connectionError = error.localizedDescription

        // Auto-reconnect
        if reconnectAttempts < maxReconnectAttempts {
            reconnectAttempts += 1
            let delay = Double(reconnectAttempts) * 2.0

            Task {
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                await MainActor.run {
                    self.webSocketTask = nil
                    self.connect()
                }
            }
        }
    }
}

// MARK: - URLSessionWebSocketDelegate

extension WebSocketService: URLSessionWebSocketDelegate {
    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didOpenWithProtocol protocol: String?
    ) {
        Task { @MainActor in
            self.isConnected = true
            self.connectionError = nil
        }
    }

    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        Task { @MainActor in
            self.isConnected = false
        }
    }
}

import Foundation

/// Service für das Laden und Speichern von Szenarien via REST API
class ScenarioService: ObservableObject {
    static let shared = ScenarioService()

    private let baseURL = "http://localhost:8080/api/scenarios"

    @Published var scenarios: [Scenario] = []
    @Published var isLoading = false
    @Published var error: String?

    private init() {}

    // MARK: - Public Methods

    /// Lädt alle Szenarien vom Server
    @MainActor
    func fetchScenarios() async {
        isLoading = true
        error = nil

        do {
            guard let url = URL(string: baseURL) else {
                throw ScenarioError.invalidURL
            }

            let (data, response) = try await URLSession.shared.data(from: url)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw ScenarioError.serverError
            }

            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            let listResponse = try decoder.decode(ScenarioListResponse.self, from: data)
            scenarios = listResponse.scenarios

        } catch {
            self.error = error.localizedDescription
            print("Fehler beim Laden der Szenarien: \(error)")
        }

        isLoading = false
    }

    /// Erstellt ein neues Szenario
    @MainActor
    func createScenario(_ scenario: ScenarioCreate) async -> Scenario? {
        do {
            guard let url = URL(string: baseURL) else {
                throw ScenarioError.invalidURL
            }

            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let encoder = JSONEncoder()
            request.httpBody = try encoder.encode(scenario)

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 201 else {
                throw ScenarioError.serverError
            }

            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            let newScenario = try decoder.decode(Scenario.self, from: data)

            // Zur Liste hinzufügen
            scenarios.append(newScenario)

            return newScenario

        } catch {
            self.error = error.localizedDescription
            print("Fehler beim Erstellen des Szenarios: \(error)")
            return nil
        }
    }

    /// Aktualisiert ein bestehendes Szenario
    @MainActor
    func updateScenario(_ scenarioId: String, update: ScenarioUpdate) async -> Scenario? {
        do {
            guard let url = URL(string: "\(baseURL)/\(scenarioId)") else {
                throw ScenarioError.invalidURL
            }

            var request = URLRequest(url: url)
            request.httpMethod = "PUT"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let encoder = JSONEncoder()
            request.httpBody = try encoder.encode(update)

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw ScenarioError.serverError
            }

            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            let updatedScenario = try decoder.decode(Scenario.self, from: data)

            // In der Liste aktualisieren
            if let index = scenarios.firstIndex(where: { $0.id == scenarioId }) {
                scenarios[index] = updatedScenario
            }

            return updatedScenario

        } catch {
            self.error = error.localizedDescription
            print("Fehler beim Aktualisieren des Szenarios: \(error)")
            return nil
        }
    }

    /// Löscht ein Szenario
    @MainActor
    func deleteScenario(_ scenarioId: String) async -> Bool {
        do {
            guard let url = URL(string: "\(baseURL)/\(scenarioId)") else {
                throw ScenarioError.invalidURL
            }

            var request = URLRequest(url: url)
            request.httpMethod = "DELETE"

            let (_, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 204 else {
                throw ScenarioError.serverError
            }

            // Aus der Liste entfernen
            scenarios.removeAll { $0.id == scenarioId }

            return true

        } catch {
            self.error = error.localizedDescription
            print("Fehler beim Löschen des Szenarios: \(error)")
            return false
        }
    }
}

// MARK: - Models

/// Szenario aus der Datenbank
struct Scenario: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let scenarioText: String
    let agentAName: String
    let agentAPrompt: String
    let agentBName: String
    let agentBPrompt: String
    let isPreset: Bool
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case scenarioText = "scenario_text"
        case agentAName = "agent_a_name"
        case agentAPrompt = "agent_a_prompt"
        case agentBName = "agent_b_name"
        case agentBPrompt = "agent_b_prompt"
        case isPreset = "is_preset"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    /// Konvertiert zu AgentConfig für Agent A
    func toAgentAConfig() -> AgentConfig {
        AgentConfig(name: agentAName, prompt: agentAPrompt)
    }

    /// Konvertiert zu AgentConfig für Agent B
    func toAgentBConfig() -> AgentConfig {
        AgentConfig(name: agentBName, prompt: agentBPrompt)
    }
}

/// Response für Szenario-Liste
struct ScenarioListResponse: Codable {
    let scenarios: [Scenario]
    let total: Int
}

/// Request zum Erstellen eines Szenarios
struct ScenarioCreate: Codable {
    let name: String
    let scenarioText: String
    let agentAName: String
    let agentAPrompt: String
    let agentBName: String
    let agentBPrompt: String

    enum CodingKeys: String, CodingKey {
        case name
        case scenarioText = "scenario_text"
        case agentAName = "agent_a_name"
        case agentAPrompt = "agent_a_prompt"
        case agentBName = "agent_b_name"
        case agentBPrompt = "agent_b_prompt"
    }
}

/// Request zum Aktualisieren eines Szenarios
struct ScenarioUpdate: Codable {
    var name: String?
    var scenarioText: String?
    var agentAName: String?
    var agentAPrompt: String?
    var agentBName: String?
    var agentBPrompt: String?

    enum CodingKeys: String, CodingKey {
        case name
        case scenarioText = "scenario_text"
        case agentAName = "agent_a_name"
        case agentAPrompt = "agent_a_prompt"
        case agentBName = "agent_b_name"
        case agentBPrompt = "agent_b_prompt"
    }
}

// MARK: - Errors

enum ScenarioError: LocalizedError {
    case invalidURL
    case serverError
    case decodingError

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Ungültige URL"
        case .serverError:
            return "Server-Fehler"
        case .decodingError:
            return "Fehler beim Dekodieren der Daten"
        }
    }
}

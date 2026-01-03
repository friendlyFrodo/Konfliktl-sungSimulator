import SwiftUI

/// Die Haupt-Chat-Ansicht
struct ChatView: View {
    @ObservedObject var viewModel: ChatViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Chat Messages
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(viewModel.messages) { message in
                            MessageBubble(message: message)
                                .id(message.id)
                        }

                        // Streaming Message
                        if let streamingMessage = viewModel.streamingMessage {
                            MessageBubble(message: streamingMessage)
                                .id("streaming")
                        }

                        // Typing Indicator
                        if let typingName = viewModel.typingAgentName,
                           viewModel.streamingMessage == nil {
                            TypingIndicator(agentName: typingName)
                                .id("typing")
                        }
                    }
                    .padding()
                }
                .onChange(of: viewModel.messages.count) { _, _ in
                    withAnimation {
                        proxy.scrollTo(viewModel.messages.last?.id, anchor: .bottom)
                    }
                }
                .onChange(of: viewModel.streamingMessage?.content) { _, _ in
                    withAnimation {
                        proxy.scrollTo("streaming", anchor: .bottom)
                    }
                }
            }

            Divider()

            // Input Area
            if viewModel.isSessionActive {
                InputArea(viewModel: viewModel)
            }
        }
        .frame(minWidth: 400, minHeight: 300)
    }
}

/// Eine einzelne Nachricht
struct MessageBubble: View {
    let message: Message

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            // Avatar
            Circle()
                .fill(avatarColor)
                .frame(width: 36, height: 36)
                .overlay(
                    Text(avatarInitial)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(.white)
                )

            VStack(alignment: .leading, spacing: 4) {
                // Name
                Text(message.agentName)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.secondary)

                // Content
                Text(message.content)
                    .font(.body)
                    .textSelection(.enabled)
                    .padding(10)
                    .background(bubbleColor)
                    .cornerRadius(12)

                // Timestamp
                if !message.isStreaming {
                    Text(message.timestamp, style: .time)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()
        }
        .opacity(message.isStreaming ? 0.8 : 1.0)
    }

    private var avatarColor: Color {
        switch message.agent {
        case .agentA:
            return .pink
        case .agentB:
            return .blue
        case .mediator, .user:
            return .green
        case .evaluator:
            return .purple
        }
    }

    private var avatarInitial: String {
        String(message.agentName.prefix(1))
    }

    private var bubbleColor: Color {
        switch message.agent {
        case .agentA:
            return Color.pink.opacity(0.15)
        case .agentB:
            return Color.blue.opacity(0.15)
        case .mediator, .user:
            return Color.green.opacity(0.15)
        case .evaluator:
            return Color.purple.opacity(0.15)
        }
    }
}

/// Typing Indicator
struct TypingIndicator: View {
    let agentName: String
    @State private var animationOffset = 0

    var body: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(Color.gray.opacity(0.3))
                .frame(width: 36, height: 36)
                .overlay(
                    Text("...")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.gray)
                )

            HStack(spacing: 4) {
                Text("\(agentName) tippt")
                    .font(.caption)
                    .foregroundColor(.secondary)

                HStack(spacing: 2) {
                    ForEach(0..<3) { index in
                        Circle()
                            .fill(Color.secondary)
                            .frame(width: 4, height: 4)
                            .offset(y: animationOffset == index ? -3 : 0)
                    }
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.gray.opacity(0.1))
            .cornerRadius(12)

            Spacer()
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 0.5).repeatForever()) {
                animationOffset = (animationOffset + 1) % 3
            }
        }
    }
}

/// Eingabebereich - Neue Architektur mit Decision Buttons
struct InputArea: View {
    @ObservedObject var viewModel: ChatViewModel

    var body: some View {
        VStack(spacing: 12) {
            // Decision Buttons (nach jedem Agent-Statement)
            if viewModel.isWaitingForDecision {
                DecisionButtons(viewModel: viewModel)
            }
            // Text-Eingabe (wenn User beitragen möchte)
            else if viewModel.isWaitingForInput {
                UserInputArea(viewModel: viewModel)
            }
            // Während Agent spricht - nichts anzeigen
            else if viewModel.typingAgentName != nil || viewModel.streamingMessage != nil {
                HStack {
                    ProgressView()
                        .scaleEffect(0.8)
                    Text("\(viewModel.typingAgentName ?? "Agent") spricht...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                }
                .padding()
            }
        }
        .background(Color(NSColor.windowBackgroundColor))
    }
}

/// Decision Buttons nach jedem Agent-Statement
struct DecisionButtons: View {
    @ObservedObject var viewModel: ChatViewModel

    var body: some View {
        VStack(spacing: 8) {
            Text("Was möchtest du tun?")
                .font(.caption)
                .foregroundColor(.secondary)

            HStack(spacing: 12) {
                // Lass anderen Agent antworten
                Button(action: viewModel.letNextAgentSpeak) {
                    HStack {
                        Image(systemName: "bubble.left.fill")
                        Text("Lass \(viewModel.suggestedNextName ?? "Agent") antworten")
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)

                // Selbst beitragen
                Button(action: viewModel.userWantsToContribute) {
                    HStack {
                        Image(systemName: "hand.raised.fill")
                        Text("Selbst beitragen")
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(Color.orange)
                    .foregroundColor(.white)
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)

                // Gespräch beenden
                Button(action: viewModel.requestEvaluation) {
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                        Text("Auswerten")
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(Color.purple)
                    .foregroundColor(.white)
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
    }
}

/// User Input Bereich
struct UserInputArea: View {
    @ObservedObject var viewModel: ChatViewModel

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Image(systemName: "hand.raised.fill")
                    .foregroundColor(.orange)
                Text("Dein Beitrag als Mediator")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()

                // Zurück zu Decision
                Button(action: { viewModel.isWaitingForInput = false; viewModel.isWaitingForDecision = true }) {
                    Text("Abbrechen")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }

            HStack(spacing: 12) {
                TextField("Deine Nachricht...", text: $viewModel.inputText)
                    .textFieldStyle(.plain)
                    .padding(10)
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(8)
                    .onSubmit {
                        viewModel.sendMessage()
                    }

                Button(action: viewModel.sendMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 28))
                        .foregroundColor(canSend ? .accentColor : .gray)
                }
                .disabled(!canSend)
                .buttonStyle(.plain)
            }
        }
        .padding()
    }

    private var canSend: Bool {
        !viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}

#Preview {
    ChatView(viewModel: ChatViewModel())
}

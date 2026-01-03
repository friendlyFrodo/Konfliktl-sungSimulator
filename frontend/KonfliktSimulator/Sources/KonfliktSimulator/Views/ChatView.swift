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

/// Eingabebereich
struct InputArea: View {
    @ObservedObject var viewModel: ChatViewModel

    var body: some View {
        VStack(spacing: 8) {
            // Status
            if viewModel.isWaitingForInput {
                HStack {
                    Image(systemName: "hand.raised.fill")
                        .foregroundColor(.orange)
                    Text("Du bist dran als \(roleDisplayName)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                }
                .padding(.horizontal)
                .padding(.top, 8)
            }

            HStack(spacing: 12) {
                // Text Input
                TextField("Nachricht eingeben...", text: $viewModel.inputText)
                    .textFieldStyle(.plain)
                    .padding(10)
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(8)
                    .disabled(!viewModel.isWaitingForInput)
                    .onSubmit {
                        viewModel.sendMessage()
                    }

                // Send Button
                Button(action: viewModel.sendMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 28))
                        .foregroundColor(canSend ? .accentColor : .gray)
                }
                .disabled(!canSend)
                .buttonStyle(.plain)

                // Eingreifen Button (während Streaming)
                if viewModel.typingAgentName != nil || viewModel.streamingMessage != nil {
                    Button(action: viewModel.intervene) {
                        HStack(spacing: 4) {
                            Image(systemName: "hand.raised.fill")
                            Text("Eingreifen")
                                .font(.caption)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Color.orange)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                    .help("Unterbreche das Gespräch und greife als Mediator ein")
                }

                // Stop/Evaluate Button
                Button(action: viewModel.stopAndEvaluate) {
                    Image(systemName: "stop.circle.fill")
                        .font(.system(size: 28))
                        .foregroundColor(.red)
                }
                .buttonStyle(.plain)
                .help("Session beenden und Evaluierung anfordern")
            }
            .padding()
        }
        .background(Color(NSColor.windowBackgroundColor))
    }

    private var canSend: Bool {
        viewModel.isWaitingForInput &&
        !viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var roleDisplayName: String {
        switch viewModel.expectedRole {
        case "mediator": return "Mediator"
        case "agent_a": return "Agent A"
        case "agent_b": return "Agent B"
        default: return viewModel.expectedRole
        }
    }
}

#Preview {
    ChatView(viewModel: ChatViewModel())
}

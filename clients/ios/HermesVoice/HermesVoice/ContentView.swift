import SwiftUI

struct ContentView: View {
    @State private var isRecording = false
    @State private var transcript = ""
    @State private var responseText = ""
    @State private var serverIP = UserDefaults.standard.string(forKey: "serverIP") ?? "192.168.1.10"
    @State private var wsClient = WebSocketClient()
    @State private var audioPlayer = AudioPlayerManager()
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                // Server IP config
                HStack {
                    Image(systemName: "server.rack")
                        .foregroundColor(.secondary)
                    TextField("Mac IP", text: $serverIP)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.decimalPad)
                        .font(.system(.body, design: .monospaced))
                        .onChange(of: serverIP) { _, new in
                            UserDefaults.standard.set(new, forKey: "serverIP")
                            wsClient.serverIP = new
                        }
                }
                .padding(.horizontal)

                // Transcript display
                VStack(alignment: .leading, spacing: 8) {
                    Text("你说:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(transcript.isEmpty ? "..." : transcript)
                        .font(.body)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                }
                .padding(.horizontal)

                // Response display
                VStack(alignment: .leading, spacing: 8) {
                    Text("回复:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(responseText.isEmpty ? "..." : responseText)
                        .font(.body)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color(.systemBlue).opacity(0.1))
                        .cornerRadius(12)
                }
                .padding(.horizontal)

                Spacer()

                // Record button
                Button(action: toggleRecording) {
                    ZStack {
                        Circle()
                            .fill(isRecording ? Color.red : Color.accentColor)
                            .frame(width: 80, height: 80)
                            .shadow(color: (isRecording ? Color.red : Color.accentColor).opacity(0.3), radius: 8, x: 0, y: 4)

                        Image(systemName: isRecording ? "stop.fill" : "mic.fill")
                            .font(.system(size: 28))
                            .foregroundColor(.white)
                    }
                }
                .disabled(wsClient.isConnected == false)
                .opacity(wsClient.isConnected ? 1 : 0.5)

                Text(isRecording ? "松开结束" : "按住说话")
                    .font(.caption)
                    .foregroundColor(.secondary)

                Spacer()
            }
            .padding(.top)
            .navigationTitle("yuanfang-brain")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { showSettings.toggle() }) {
                        Image(systemName: "gear")
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView(serverIP: $serverIP, wsClient: wsClient)
            }
            .onAppear {
                wsClient.serverIP = serverIP
                wsClient.onTranscript = { t in
                    DispatchQueue.main.async { transcript = t }
                }
                wsClient.onLLMChunk = { t in
                    DispatchQueue.main.async { responseText += t }
                }
                wsClient.onTTSChunk = { data in
                    audioPlayer.appendAudioData(data)
                }
                wsClient.onTTSDone = {
                    audioPlayer.play()
                }
                wsClient.connect()
            }
            .onDisappear {
                wsClient.disconnect()
            }
        }
    }

    func toggleRecording() {
        if isRecording {
            wsClient.stopRecording()
        } else {
            transcript = ""
            responseText = ""
            wsClient.startRecording()
        }
        isRecording.toggle()
    }
}

struct SettingsView: View {
    @Binding var serverIP: String
    let wsClient: WebSocketClient
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("服务器") {
                    TextField("Mac IP 地址", text: $serverIP)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.decimalPad)
                        .font(.system(.body, design: .monospaced))
                }
                Section {
                    Button(wsClient.isConnected ? "已连接" : "连接") {
                        wsClient.serverIP = serverIP
                        wsClient.connect()
                    }
                    .disabled(wsClient.isConnected)
                }
            }
            .navigationTitle("设置")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("完成") { dismiss() }
                }
            }
        }
    }
}

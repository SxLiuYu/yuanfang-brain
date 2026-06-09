import Foundation
import AVFoundation

class WebSocketClient: NSObject, URLSessionWebSocketDelegate {
    var serverIP = "192.168.1.10"
    private var session: URLSession!
    private var wsTask: URLSessionWebSocketTask?
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?

    var isConnected = false
    var onTranscript: ((String) -> Void)?
    var onLLMChunk: ((String) -> Void)?
    var onTTSChunk: ((Data) -> Void)?
    var onTTSDone: (() -> Void)?

    override init() {
        super.init()
        let config = URLSessionConfiguration.default
        session = URLSession(configuration: config, delegate: self, delegateQueue: .main)
    }

    func connect() {
        let url = URL(string: "ws://\(serverIP):7001/ws")!
        wsTask = session.webSocketTask(with: url)
        wsTask?.resume()
        receiveMessage()
    }

    func disconnect() {
        stopRecording()
        wsTask?.cancel(with: .normalClosure, reason: nil)
        wsTask = nil
        isConnected = false
    }

    func startRecording() {
        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker])
            try audioSession.setActive(true)
        } catch {
            print("AudioSession error: \(error)")
            return
        }

        audioEngine = AVAudioEngine()
        inputNode = audioEngine?.inputNode
        let format = inputNode?.outputFormat(forBus: 0)

        inputNode?.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            guard let pcm = self?.convertBufferToPCM(buffer) else { return }
            self?.sendAudioData(pcm)
        }

        do {
            try audioEngine?.start()
        } catch {
            print("AudioEngine start error: \(error)")
        }
    }

    func stopRecording() {
        inputNode?.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        inputNode = nil
    }

    private func convertBufferToPCM(_ buffer: AVAudioPCMBuffer) -> Data {
        let channelCount = 1
        let bufferSize = buffer.frameLength
        guard let channelData = buffer.floatChannelData?[0] else { return Data() }
        var pcm = Data()
        for i in 0..<Int(bufferSize) {
            let sample = channelData[i]
            var pcmSample = Int16(sample * Float(Int16.max))
            pcm.append(Data(bytes: &pcmSample, count: 2))
        }
        return pcm
    }

    private func sendAudioData(_ data: Data) {
        guard isConnected else { return }
        let msg = URLSessionWebSocketTask.Message.data(data)
        wsTask?.send(msg) { error in
            if let e = error { print("WS send error: \(e)") }
        }
    }

    private func receiveMessage() {
        wsTask?.receive { [weak self] result in
            switch result {
            case .success(let msg):
                switch msg {
                case .string(let text):
                    self?.handleTextMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self?.handleTextMessage(text)
                    }
                @unknown default:
                    break
                }
                self?.receiveMessage()
            case .failure(let e):
                print("WS receive error: \(e)")
                self?.isConnected = false
            }
        }
    }

    private func handleTextMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        switch type {
        case "hello":
            isConnected = true
        case "transcript":
            if let d = json["data"] as? [String: Any], let t = d["text"] as? String {
                onTranscript?(t)
            }
        case "llm_chunk":
            if let d = json["data"] as? [String: Any], let t = d["text"] as? String {
                onLLMChunk?(t)
            }
        case "tts_chunk":
            if let d = json["data"] as? [String: Any], let b64 = d["audio"] as? String,
               let audioData = Data(base64Encoded: b64) {
                onTTSChunk?(audioData)
            }
        case "tts_done":
            onTTSDone?()
        default:
            break
        }
    }

    // URLSessionWebSocketDelegate
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        print("WS connected")
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        isConnected = false
        stopRecording()
    }
}

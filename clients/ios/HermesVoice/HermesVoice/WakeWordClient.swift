import Foundation
import AVFoundation
import AudioToolbox

/// Wake-word detection client that streams 16 kHz mono PCM to /ws/wake
/// and plumbs wake events back into the existing WebSocketClient.
class WakeWordClient: NSObject, URLSessionWebSocketDelegate {
    var serverIP = "192.168.1.10"

    /// Called when a wake word is detected.
    var onWakeDetected: ((String, Float) -> Void)?

    /// The main voice WebSocket client — caller initialises this before connecting.
    weak var voiceClient: WebSocketClient?

    private var session: URLSession!
    private var wsTask: URLSessionWebSocketTask?
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private(set) var isConnected = false

    /// Short "bump" tone played on wake detection.
    private var wakeTonePlayer: AVAudioPlayer?

    override init() {
        super.init()
        let config = URLSessionConfiguration.default
        session = URLSession(configuration: config, delegate: self, delegateQueue: .main)
    }

    // MARK: - Public API

    func connect() {
        let url = URL(string: "ws://\(serverIP):7001/ws/wake")!
        wsTask = session.webSocketTask(with: url)
        wsTask?.resume()
        receiveMessage()
    }

    func disconnect() {
        stopListening()
        wsTask?.cancel(with: .normalClosure, reason: nil)
        wsTask = nil
        isConnected = false
    }

    func startListening() {
        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker])
            try audioSession.setActive(true)
        } catch {
            print("[WakeWord] AudioSession error: \(error)")
            return
        }

        audioEngine = AVAudioEngine()
        inputNode = audioEngine?.inputNode
        let format = inputNode?.outputFormat(forBus: 0)

        inputNode?.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            guard let self = self, self.isConnected else { return }
            guard let pcm = self.convertBufferToPCM(buffer) else { return }
            self.sendAudioData(pcm)
        }

        do {
            try audioEngine?.start()
        } catch {
            print("[WakeWord] AudioEngine start error: \(error)")
        }
    }

    func stopListening() {
        inputNode?.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        inputNode = nil
    }

    // MARK: - Audio conversion

    private func convertBufferToPCM(_ buffer: AVAudioPCMBuffer) -> Data? {
        let bufferSize = buffer.frameLength
        guard let channelData = buffer.floatChannelData?[0] else { return nil }
        var pcm = Data()
        pcm.reserveCapacity(Int(bufferSize) * 2)
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
            if let e = error { print("[WakeWord] WS send error: \(e)") }
        }
    }

    // MARK: - Receive loop

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
                print("[WakeWord] WS receive error: \(e)")
                self?.isConnected = false
            }
        }
    }

    private func handleTextMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }

        // Wake event
        if let event = json["event"] as? String, event == "wake" {
            let model = json["model"] as? String ?? "alexa"
            let score = (json["score"] as? NSNumber)?.floatValue ?? 0.0

            playWakeTone()
            onWakeDetected?(model, score)
            return
        }

        // hello
        if let type = json["type"] as? String, type == "hello" {
            isConnected = true
        }
    }

    // MARK: - Wake tone

    private func playWakeTone() {
        // Generate a short 880 Hz sine burst (≈100 ms) using AudioToolbox
        let sampleRate: Double = 16000
        let duration: Double = 0.1
        let frequency: Double = 880.0
        let frameCount = Int(sampleRate * duration)

        var samples = [Float](repeating: 0, count: frameCount)
        for i in 0..<frameCount {
            samples[i] = sin(2.0 * .pi * frequency * Double(i) / sampleRate) * 0.5
        }

        // Convert to int16 PCM
        var pcmData = Data()
        for s in samples {
            var sample = Int16(s * Float(Int16.max))
            pcmData.append(Data(bytes: &sample, count: 2))
        }

        // Wrap in a simple WAV header (44-byte header + samples)
        var wavFile = Data()
        // RIFF header
        wavFile.append("RIFF".data(using: .ascii)!)
        let fileSize = UInt32(44 + pcmData.count - 8)
        wavFile.append(Data(bytes: [fileSize], count: 4))
        wavFile.append("WAVE".data(using: .ascii)!)

        // fmt chunk
        wavFile.append("fmt ".data(using: .ascii)!)
        var fmtSize: UInt32 = 16
        wavFile.append(Data(bytes: &fmtSize, count: 4))
        var audioFormat: UInt16 = 1  // PCM
        wavFile.append(Data(bytes: &audioFormat, count: 2))
        var numChannels: UInt16 = 1
        wavFile.append(Data(bytes: &numChannels, count: 2))
        var sr: UInt32 = UInt32(sampleRate)
        wavFile.append(Data(bytes: &sr, count: 4))
        var byteRate: UInt32 = UInt32(sampleRate) * 2
        wavFile.append(Data(bytes: &byteRate, count: 4))
        var blockAlign: UInt16 = 2
        wavFile.append(Data(bytes: &blockAlign, count: 2))
        var bitsPerSample: UInt16 = 16
        wavFile.append(Data(bytes: &bitsPerSample, count: 2))

        // data chunk
        wavFile.append("data".data(using: .ascii)!)
        var dataSize = UInt32(pcmData.count)
        wavFile.append(Data(bytes: &dataSize, count: 4))
        wavFile.append(pcmData)

        wakeTonePlayer = try? AVAudioPlayer(data: wavFile)
        wakeTonePlayer?.volume = 0.8
        wakeTonePlayer?.play()
    }

    // MARK: - URLSessionWebSocketDelegate

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        print("[WakeWord] WS connected")
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        isConnected = false
        stopListening()
    }
}
import Foundation
import AVFoundation

class AudioPlayerManager: NSObject, AVAudioPlayerDelegate {
    private var player: AVAudioPlayer?
    private var audioBuffers: [Data] = []
    private var isPlaying = false

    func appendAudioData(_ data: Data) {
        audioBuffers.append(data)
    }

    func play() {
        guard !audioBuffers.isEmpty else { return }

        let combined = audioBuffers.reduce(Data()) { $0 + $1 }
        audioBuffers.removeAll()

        do {
            player = try AVAudioPlayer(data: combined)
            player?.delegate = self
            player?.play()
            isPlaying = true
        } catch {
            print("AudioPlayer error: \(error)")
        }
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        isPlaying = false
    }
}

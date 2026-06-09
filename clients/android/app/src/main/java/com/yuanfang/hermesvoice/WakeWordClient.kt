package com.yuanfang.hermesvoice

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.ToneGenerator
import androidx.core.app.ActivityCompat
import okhttp3.*
import okio.ByteString
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Wake-word detection client that streams 16 kHz mono PCM to /ws/wake.
 * On wake detection, plays a short tone and notifies the caller via onWakeDetected.
 */
class WakeWordClient(
    private val onWakeDetected: (model: String, score: Float) -> Unit
) {
    private var ws: WebSocket? = null
    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    /** The main voice WebSocket — caller sets this before connecting. */
    var voiceWebSocket: WebSocketClient? = null

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    fun connect(url: String) {
        val request = Request.Builder().url(url).build()
        ws = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                startRecording()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleTextMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                stopRecording()
            }
        })
    }

    fun disconnect() {
        stopRecording()
        ws?.close(1000, null)
        ws = null
    }

    @Suppress("MissingPermission")
    fun startRecording() {
        val sampleRate = 16000
        val bufferSize = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )

        isRecording = true
        audioRecord?.startRecording()

        thread {
            val buffer = ShortArray(bufferSize / 2)
            while (isRecording) {
                val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (read > 0) {
                    val pcm = ByteArray(read * 2)
                    for (i in 0 until read) {
                        val sample = buffer[i].toInt()
                        pcm[i * 2] = (sample and 0xFF).toByte()
                        pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
                    }
                    ws?.send(ByteString.of(*pcm))
                }
            }
        }
    }

    fun stopRecording() {
        isRecording = false
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
    }

    private fun handleTextMessage(text: String) {
        try {
            val json = JSONObject(text)

            // Wake event
            if (json.has("event")) {
                val event = json.getString("event")
                if (event == "wake") {
                    val model = json.optString("model", "alexa")
                    val score = json.optDouble("score", 0.0).toFloat()
                    playWakeTone()
                    onWakeDetected(model, score)
                }
                return
            }

            // hello / other WS types
            val type = json.optString("type", "")
            if (type == "hello") {
                // connected
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun playWakeTone() {
        try {
            val tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)
            tone.startTone(ToneGenerator.TONE_PROP_BEEP, 150)
            // Release after playback
            thread {
                Thread.sleep(200)
                tone.release()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
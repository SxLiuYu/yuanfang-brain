package com.yuanfang.hermesvoice

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.core.app.ActivityCompat
import okhttp3.*
import okio.ByteString
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class WebSocketClient(
    private val onConnect: () -> Unit,
    private val onDisconnect: () -> Unit,
    private val onTranscript: (String) -> Unit,
    private val onLLMChunk: (String) -> Unit,
    private val onTTSChunk: (ByteArray) -> Unit,
    private val onTTSDone: () -> Unit
) {
    private var ws: WebSocket? = null
    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    fun connect(url: String) {
        val request = Request.Builder().url(url).build()
        ws = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                onConnect()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleTextMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                onDisconnect()
            }
        })
    }

    fun disconnect() {
        stopRecording()
        ws?.close(1000, null)
        ws = null
    }

    fun startRecording() {
        val sampleRate = 16000
        val bufferSize = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        if (ActivityCompat.checkSelfPermission(
                androidx.compose.ui.platform.LocalContext.current,
                Manifest.permission.RECORD_AUDIO
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

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
            val type = json.getString("type")
            val data = json.optJSONObject("data")

            when (type) {
                "hello" -> onConnect()
                "transcript" -> {
                    val t = data?.optString("text") ?: ""
                    onTranscript(t)
                }
                "llm_chunk" -> {
                    val t = data?.optString("text") ?: ""
                    onLLMChunk(t)
                }
                "tts_chunk" -> {
                    val b64 = data?.optString("audio") ?: ""
                    val decoded = Base64.getDecoder().decode(b64)
                    onTTSChunk(decoded)
                }
                "tts_done" -> onTTSDone()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}

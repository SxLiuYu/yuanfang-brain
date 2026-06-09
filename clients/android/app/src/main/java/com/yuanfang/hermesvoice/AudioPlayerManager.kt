package com.yuanfang.hermesvoice

import android.content.Context
import android.media.MediaPlayer
import android.net.Uri
import androidx.compose.ui.platform.LocalContext
import java.io.File
import java.io.FileOutputStream

object AudioPlayerManager {
    private val audioBuffers = mutableListOf<ByteArray>()
    private var player: MediaPlayer? = null

    fun appendData(data: ByteArray) {
        audioBuffers.add(data)
    }

    fun play() {
        if (audioBuffers.isEmpty()) return

        val combined = audioBuffers.fold(ByteArray(0)) { acc, bytes -> acc + bytes }
        audioBuffers.clear()

        try {
            val tempFile = File.createTempFile("tts", ".mp3")
            FileOutputStream(tempFile).use { it.write(combined) }
            tempFile.deleteOnExit()

            player?.release()
            player = MediaPlayer().apply {
                setDataSource(File(tempFile.absolutePath).toURI().toString())
                prepare()
                start()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}

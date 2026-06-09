package com.yuanfang.hermesvoice

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.yuanfang.hermesvoice.ui.theme.HermesVoiceTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okio.ByteString
import java.util.*
import kotlin.concurrent.thread

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { HermesVoiceTheme { HermesVoiceApp() } }
    }
}

@Composable
fun HermesVoiceApp() {
    val context = LocalContext.current
    var serverIP by remember { mutableStateOf("192.168.1.10") }
    var isRecording by remember { mutableStateOf(false) }
    var transcript by remember { mutableStateOf("") }
    var responseText by remember { mutableStateOf("") }
    var isConnected by remember { mutableStateOf(false) }

    val wsClient = remember {
        WebSocketClient(
            onConnect = { isConnected = true },
            onDisconnect = { isConnected = false },
            onTranscript = { t -> transcript = t },
            onLLMChunk = { t -> responseText += t },
            onTTSChunk = { data -> AudioPlayerManager.appendData(data) },
            onTTSDone = { AudioPlayerManager.play() }
        )
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Server IP
        OutlinedTextField(
            value = serverIP,
            onValueChange = { serverIP = it },
            label = { Text("Mac IP") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = {
                wsClient.connect("ws://$serverIP:7001/ws")
                Toast.makeText(context, if (isConnected) "已连接" else "连接中...", Toast.LENGTH_SHORT).show()
            },
            enabled = !isConnected
        ) {
            Text(if (isConnected) "已连接" else "连接")
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Transcript
        Card(modifier = Modifier.fillMaxWidth().height(100.dp)) {
            Text(
                text = if (transcript.isEmpty()) "你说: ..." else "你说: $transcript",
                modifier = Modifier.padding(16.dp)
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Response
        Card(modifier = Modifier.fillMaxWidth().height(100.dp)) {
            Text(
                text = if (responseText.isEmpty()) "回复: ..." else "回复: $responseText",
                modifier = Modifier.padding(16.dp)
            )
        }

        Spacer(modifier = Modifier.weight(1f))

        // Record button
        Button(
            onClick = {
                if (isRecording) {
                    wsClient.stopRecording()
                } else {
                    transcript = ""
                    responseText = ""
                    wsClient.startRecording()
                }
                isRecording = !isRecording
            },
            modifier = Modifier.size(80.dp),
            shape = CircleShape,
            enabled = isConnected,
            colors = ButtonDefaults.buttonColors(
                containerColor = if (isRecording) Color.Red else MaterialTheme.colorScheme.primary
            )
        ) {
            Icon(
                imageVector = if (isRecording) androidx.compose.material.icons.Icons.Default.Stop else androidx.compose.material.icons.Icons.Default.Mic,
                contentDescription = null,
                tint = Color.White
            )
        }

        Text(
            text = if (isRecording) "松开结束" else "按住说话",
            fontSize = 12.sp,
            color = Color.Gray
        )

        Spacer(modifier = Modifier.height(32.dp))
    }
}

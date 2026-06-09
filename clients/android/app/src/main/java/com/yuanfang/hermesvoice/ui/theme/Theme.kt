package com.yuanfang.hermesvoice.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF6750A4),
    secondary = Color(0xFF625B71),
    tertiary = Color(0xFF7D5260)
)

@Composable
fun HermesVoiceTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DarkColorScheme) { content() }
}

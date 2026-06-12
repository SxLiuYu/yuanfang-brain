Waveshare ESP32-S3-Touch-AMOLED-2.06 二开手册
(2026-06-11 基于 wiki + 淘宝商品详情 + 2 个 CC 调研报告整合)
============================================================

一、硬件真盘
- MCU: ESP32-S3R8 (Xtensa LX7 双核 240 MHz)
- 内存: 512KB SRAM + 8MB PSRAM + 32MB Flash
- 屏幕: 2.06" AMOLED 410×502, CO5300 QSPI
- 触屏: FT3168 I2C
- IMU: QMI8658 (6 轴)
- RTC: PCF85063 (新发现)
- PMU: AXP2101
- 音频: ES8311 codec + ES7210 ADC + 板载麦 + 双麦克风 + 扬声器
- 存储: TF 卡槽 (SDMMC, GPIO1/2/3/17)
- 物理: Type-C USB + PWR 按键(GPIO10) + BOOT 按键(GPIO0) + 双麦克风 + 扬声器
- 表带槽: 22mm 平头(可换普通 22mm 表带)
- 厂商: Waveshare / 微雪电子
- 淘宝: 1688 offerId=953950964185, ¥45-56

二、完整引脚定义(2026-06-11 最新确认)
LCD (QSPI):
  LCD_SDIO0=4, SDIO1=5, SDIO2=6, SDIO3=7, SCLK=11, CS=12, RESET=8, TE=13
Touch (I2C + INT):
  IIC_SDA=15, IIC_SCL=14, TP_INT=38, TP_RESET=9
SD (SDMMC):
  MOSI=1, SCK=2, MISO=3, CS=17
IMU QMI8658 (I2C + INT):
  INT=21, SDA=15, SCL=14
RTC PCF85063 (I2C + INT):
  INT=39, SDA=15, SCL=14
PMIC AXP2101 (I2C):
  SDA=15, SCL=14
Audio Codec ES8311 (I2C + I2S):
  SDA=15, SCL=14, MCLK=16, SCLK=41
Audio ADC ES7210 (I2S):
  ASDOUT=42, LRCK=45, DSDIN=40, PA_CTRL=46
启动/电源:
  BOOT=GPIO0 (启动模式选择)
  PWR=GPIO10 (电源键, 长按 ≥6秒 关机)

三、3 个必看 URL
1. https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-2.06 (官方 Wiki)
2. https://github.com/78/xiaozhi-esp32/releases/tag/v2.2.6 (预编译小智固件)
3. https://github.com/espressif/esp-brookesia (官方 UI 框架)
4. https://github.com/78/xiaozhi-assets-generator (在线改 UI 免编译)
5. https://docs.espressif.com/projects/esptool/en/latest/esp32s3/ (esptool 烧录)

四、框架选型
- Arduino v3.2.0 (examples/Arduino-v3.2.0/, 8 个例程: HelloWorld/GFX/LVGL/QMI8658/AXP2101/SD/ES8311)
- ESP-IDF v5.4.2 (examples/ESP-IDF-v5.4.2/, 6 个例程: AXP2101/lvgl/esp-brookesia/沉浸感/频谱/视频)
- 当前预装: ESP-Brookesia demo (Waveshare/ESP-Brookesia 菜单)

五、Mac 烧录 5 步
1. 装工具: pip install esptool (或 brew install esptool)
2. 区分数据线 (iPhone 17 自带 = 充电线, 不可用; 推荐: 绿联 USB-C 全功能 ¥25, 贝尔金 F2CU023 ¥59)
   自测: iPhone 连 Mac, Finder 左侧出现 iPhone = 数据线
   物理看: USB-C 头手电筒照, 满 24 pin = 数据线
3. 进入烧录模式 (二选一):
   A) 按住 BOOT(GPIO0) + 按 RESET(EN) + 先松 RESET + 再松 BOOT (经典 ESP 烧录方式)
   B) 按住 PWR ≥ 6 秒 (Waveshare 2.06 特殊硬重启, 适用于固件死机情况)
4. 验证: ls /dev/cu.* 应出现 /dev/cu.usbmodem* 或 /dev/cu.wchusb*
   或 ioreg -p IOUSB -l | grep -iE "ESP32|Silicon|CH340|CP210|FTDI"
5. 烧录命令 (16MB Flash, 4 bin):
   esptool.py --chip esp32s3 -p /dev/cu.usbmodemXXXX write_flash \
     0x0     bootloader.bin \
     0x8000  partitions.bin \
     0x10000 xiaozhi.bin \
     0x3F0000 ota_data_initial.bin
   (整片擦除: esptool.py --chip esp32s3 -p /dev/cu.usbmodemXXXX erase-flash)

六、3 路径选择
A (新手/直接用) - 刷小智预编译固件:
  下载 https://github.com/78/xiaozhi-esp32/releases/download/v2.2.6/v2.2.6_waveshare-esp32-s3-touch-amoled-2.06.zip
  解压跑 flash_download.sh
  微信扫码配网 + 用
  缺点: 默认连 xiaozhi.me, 改服务器要自编译

B (深度定制) - 自己编译小智:
  git clone https://github.com/78/xiaozhi-esp32
  编辑 main/Kconfig.projbuild:
    CONFIG_XIAOZHI_DEFAULT_WS_URL="ws://192.168.1.10:7103"
  选择 board: waveshare/esp32-s3-touch-amoled-2.06
  idf.py set-target esp32s3
  idf.py build
  idf.py -p /dev/cu.usbmodemXXXX flash monitor

C (完全自定) - ESP-Brookesia + LVGL:
  idf.py create-project-from-example 选 agent/xiaozhi 示例
  自己写 UI / 加 GPIO / 改协议

七、接 yuanfang-brain (Mac 192.168.1.10:7103)
协议差距表:
- WebSocket: ✅ 一致
- 鉴权头: ❌ 小智 4 个头 (Authorization/Device-Id/Client-Id/Protocol-Version), yuanfang-brain 无
- Hello 握手: ❌ 小智 hello JSON, yuanfang-brain 无
- 音频格式: ❌ 小智 OPUS 16kHz 二进制, yuanfang-brain PCM 16k/16bit Base64
- 消息类型: ❌ 小智 listen/stt/tts/llm/mcp/abort, yuanfang-brain text/audio/reply
- MCP IoT: ❌ 小智 JSON-RPC 2.0, yuanfang-brain intent JSON

3 选 1 接通:
1. 写 ESP32 端固件 (OPUS→PCM + 改消息)
2. yuanfang-brain 加小智协议适配器 (voice/xiaozhi_server.py)
3. 跑 xinnan-tech/xiaozhi-esp32-server (Python 完整协议服务器)

八、最常见坑 (已踩)
| 坑 | 修 |
|---|---|
| Mac 看不到 /dev/cu | 换数据线 + 装 CP2102/CH343 驱动 + BOOT+RESET |
| 烧录失败 | 16MB Flash 用 16m.csv 分区表 |
| WiFi 配网失败 | 手机 + Mac 同一局域网 |
| 改不了默认服务器 | 改 CONFIG_XIAOZHI_DEFAULT_WS_URL 自己编译 |
| v2 升 v1 白屏 | 分区表不兼容, 全量重刷 |
| USB 串口掉了 | 按 PWR ≥ 6 秒硬重启 |
| ESP-Brookesia demo Mac 看不到 | 正常, 该固件不打开 USB CDC, 刷小智后才开 |

九、当前真盘状态 (2026-06-11 22:55)
- 板子: 屏幕亮, ESP-Brookesia demo 固件
- Mac 看不到: ioreg 无 ESP32 (符合预期, demo 固件不启用 USB CDC)
- 数据线: 已确认是数据线
- 下一步: 刷小智 v2.2.6 预编译固件 → 重查 ioreg → 应该能看到 /dev/cu.usbmodem*

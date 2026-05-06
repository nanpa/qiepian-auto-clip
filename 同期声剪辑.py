import sys, os, re, datetime, subprocess, shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QSlider)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl, QTime

class MiniCutterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini 自动剪辑预览编辑器 - 最终稳定版")
        self.resize(1200, 900)
        self.source_path = ""
        # 默认 ffmpeg.exe 放在程序同级目录下
        self.ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        self.init_ui()
        self.player.positionChanged.connect(self.update_slider)
        self.player.durationChanged.connect(self.update_duration)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # --- 左侧布局 ---
        left_layout = QVBoxLayout()
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black; border-radius: 5px;")
        self.player.setVideoOutput(self.video_widget)
        left_layout.addWidget(self.video_widget, 8) 

        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.set_position)
        left_layout.addWidget(self.slider)

        ctrl_box = QHBoxLayout()
        self.btn_play = QPushButton("播放/暂停")
        self.btn_play.clicked.connect(self.toggle_play)
        self.label_time = QLabel("00:00 / 00:00")
        ctrl_box.addWidget(self.btn_play); ctrl_box.addWidget(self.label_time); ctrl_box.addStretch()
        left_layout.addLayout(ctrl_box)

        left_layout.addWidget(QLabel("粘贴内容 (Markdown 列表或 SRT 文本):"))
        self.md_input = QTextEdit()
        self.md_input.setFixedHeight(150)
        left_layout.addWidget(self.md_input)
        
        btn_box = QHBoxLayout()
        self.btn_parse = QPushButton("🔍 智能追加解析"); self.btn_parse.setFixedHeight(40)
        self.btn_parse.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
        self.btn_parse.clicked.connect(self.parse_md)
        self.btn_clear = QPushButton("🗑️ 清空列表"); self.btn_clear.clicked.connect(self.clear_list)
        btn_box.addWidget(self.btn_parse, 3); btn_box.addWidget(self.btn_clear, 1)
        left_layout.addLayout(btn_box)
        main_layout.addLayout(left_layout, 7)

        # --- 右侧布局 ---
        right_layout = QVBoxLayout()
        btn_select = QPushButton("📁 1. 导入原始素材"); btn_select.setFixedHeight(45); btn_select.clicked.connect(self.select_source)
        right_layout.addWidget(btn_select)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["开始", "结束", "内容"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemClicked.connect(self.on_item_clicked)
        right_layout.addWidget(self.table)

        self.btn_export = QPushButton("💾 2. 一键导出 (视频+SRT)"); self.btn_export.setFixedHeight(65)
        self.btn_export.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; font-size: 18px;")
        self.btn_export.clicked.connect(self.export_video)
        right_layout.addWidget(self.btn_export)
        main_layout.addLayout(right_layout, 5)

    def select_source(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择素材", "", "Media (*.mp4 *.m4a *.mp3 *.mov *.mkv *.wav)")
        if file:
            self.source_path = os.path.abspath(file)
            self.player.setSource(QUrl.fromLocalFile(self.source_path))

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()

    def update_slider(self, pos):
        if not self.slider.isSliderDown(): self.slider.setValue(pos)
        curr = QTime(0, 0).addMSecs(pos).toString("mm:ss")
        dur = QTime(0, 0).addMSecs(self.player.duration()).toString("mm:ss")
        self.label_time.setText(f"{curr} / {dur}")

    def update_duration(self, dur): self.slider.setRange(0, dur)
    def set_position(self, pos): self.player.setPosition(pos)

    def on_item_clicked(self, item):
        start_ts = self.table.item(item.row(), 0).text()
        self.player.setPosition(self.ts_to_msecs(start_ts))
        self.player.play()

    def ts_to_msecs(self, ts):
        ts = ts.strip().replace(',', '.')
        try:
            t = datetime.datetime.strptime(ts, "%H:%M:%S.%f") if '.' in ts else datetime.datetime.strptime(ts, "%H:%M:%S")
            return int((t.hour * 3600 + t.minute * 60 + t.second) * 1000 + t.microsecond / 1000)
        except: return 0

    def clear_list(self): self.table.setRowCount(0)

    def parse_md(self):
        md = self.md_input.toPlainText().strip()
        pattern = r'(\d{2}:\d{2}:\d{2}[,. ]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,. ]\d{3})\s*(.*)'
        matches = re.findall(pattern, md)
        if not matches: return QMessageBox.warning(self, "解析失败", "格式不匹配，请确保包含 00:00:00.000 格式")
        for start, end, raw_text in matches:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(start))
            self.table.setItem(row, 1, QTableWidgetItem(end))
            self.table.setItem(row, 2, QTableWidgetItem(raw_text.replace('|', '').strip()))
        self.table.scrollToBottom(); self.md_input.clear()

    def export_video(self):
        if not self.source_path or self.table.rowCount() == 0: return
        
        source_dir = os.path.dirname(self.source_path)
        name_part, ext_part = os.path.splitext(os.path.basename(self.source_path))
        timestamp = datetime.datetime.now().strftime('%H%M')
        
        save_path = os.path.abspath(os.path.join(source_dir, f"{name_part}_精剪_{timestamp}{ext_part}"))
        srt_path = os.path.abspath(os.path.join(source_dir, f"{name_part}_精剪_{timestamp}.srt"))
        temp_dir = os.path.abspath(os.path.join(os.getcwd(), "temp_render"))

        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        is_audio = ext_part.lower() in ['.m4a', '.mp3', '.wav', '.aac']
        clips = []; srt_content = []; current_timeline = 0.0

        try:
            for i in range(self.table.rowCount()):
                s_val, e_val, text = self.table.item(i,0).text(), self.table.item(i,1).text(), self.table.item(i,2).text()
                s_sec = self.ts_to_msecs(s_val)/1000
                dur = (self.ts_to_msecs(e_val) - self.ts_to_msecs(s_val))/1000
                if dur <= 0: continue

                clip_path = os.path.join(temp_dir, f"clip_{i}{ext_part}")
                
                # --- 标准快速剪辑命令 ---
                # 将 -ss 放在 -i 前实现快速搜索，-i 后实现精准切割
                cmd = [self.ffmpeg_path, "-y", "-ss", str(s_sec), "-t", str(dur), "-i", self.source_path]
                
                if is_audio:
                    # 音频强制重新编码以防元数据错误，且保证拼接平滑
                    cmd += ["-c:a", "aac", "-b:a", "192k", clip_path]
                else:
                    # 视频优先使用 copy 模式（极速且无损）
                    cmd += ["-c", "copy", clip_path]
                
                res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                if not os.path.exists(clip_path):
                    raise Exception(f"片段 {i+1} 生成失败。\n原因：{res.stderr}")

                clips.append(clip_path)
                start_srt = QTime(0, 0).addMSecs(int(current_timeline * 1000)).toString("HH:mm:ss,zzz")
                end_srt = QTime(0, 0).addMSecs(int((current_timeline + dur) * 1000)).toString("HH:mm:ss,zzz")
                srt_content.append(f"{i+1}\n{start_srt} --> {end_srt}\n{text}\n")
                current_timeline += dur

            # --- 合并片段 ---
            list_file = os.path.join(temp_dir, "list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for c in clips: f.write(f"file '{c.replace('\\', '/')}'\n")
            
            # 使用 concat 协议合并
            merge_cmd = [self.ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", save_path]
            subprocess.run(merge_cmd, capture_output=True, check=True)
            
            # 写入配套字幕
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_content))
            
            QMessageBox.information(self, "大功告成", f"文件已生成在：\n{save_path}")
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MiniCutterApp()
    win.show()
    sys.exit(app.exec())
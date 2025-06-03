import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import threading # 処理中のGUIフリーズを防ぐために使用

class VideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("動画一括圧縮ツール (FFmpeg)")
        self.root.geometry("700x600") # ウィンドウサイズ調整

        self.input_files = []

        # --- スタイル設定 ---
        style = ttk.Style()
        style.configure("TButton", padding=5, font=('Helvetica', 10))
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TEntry", padding=5, font=('Helvetica', 10))
        style.configure("TCombobox", padding=5, font=('Helvetica', 10))

        # --- ファイル選択フレーム ---
        file_frame = ttk.LabelFrame(root, text="動画ファイル選択", padding=10)
        file_frame.pack(padx=10, pady=10, fill="x")

        self.file_listbox = tk.Listbox(file_frame, selectmode=tk.EXTENDED, width=70, height=8)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="ファイル追加", command=self.add_files).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="選択削除", command=self.remove_selected_files).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="全クリア", command=self.clear_file_list).pack(fill="x", pady=2)

        # --- 設定フレーム ---
        settings_frame = ttk.LabelFrame(root, text="圧縮設定", padding=10)
        settings_frame.pack(padx=10, pady=5, fill="x")

        # FPS
        ttk.Label(settings_frame, text="フレームレート (fps):").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.fps_var = tk.StringVar(value="5")
        fps_options = ["1", "5", "10", "15", "24", "30"]
        self.fps_combo = ttk.Combobox(settings_frame, textvariable=self.fps_var, values=fps_options, width=10)
        self.fps_combo.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        # 品質 (CRF)
        ttk.Label(settings_frame, text="品質 (CRF, 小さいほど高画質):").grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.crf_var = tk.StringVar(value="32") # パワポ向けなので高圧縮寄り
        crf_options = [str(i) for i in range(18, 41)] # 18-40 の範囲
        self.crf_combo = ttk.Combobox(settings_frame, textvariable=self.crf_var, values=crf_options, width=10)
        self.crf_combo.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        # 音声ビットレート
        ttk.Label(settings_frame, text="音声ビットレート:").grid(row=2, column=0, sticky="w", padx=5, pady=3)
        self.audio_bitrate_var = tk.StringVar(value="64k")
        audio_options = ["32k", "48k", "64k", "96k", "128k", "copy"]
        self.audio_bitrate_combo = ttk.Combobox(settings_frame, textvariable=self.audio_bitrate_var, values=audio_options, width=10)
        self.audio_bitrate_combo.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(settings_frame, text="( 'copy' で音声無変換 )").grid(row=2, column=2, sticky="w", padx=5, pady=3)


        # --- 出力先フレーム ---
        output_frame = ttk.LabelFrame(root, text="出力先", padding=10)
        output_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(output_frame, text="出力フォルダ:").pack(side=tk.LEFT, padx=5)
        self.output_dir_var = tk.StringVar()
        self.output_dir_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, width=50)
        self.output_dir_entry.pack(side=tk.LEFT, expand=True, fill="x", padx=5)
        ttk.Button(output_frame, text="参照...", command=self.select_output_directory).pack(side=tk.LEFT, padx=5)

        # --- 実行フレーム ---
        action_frame = ttk.Frame(root, padding=10)
        action_frame.pack(fill="x")

        self.compress_button = ttk.Button(action_frame, text="圧縮開始", command=self.start_compression_thread)
        self.compress_button.pack(pady=10)
        
        # --- 進捗表示フレーム ---
        progress_frame = ttk.LabelFrame(root, text="進捗", padding=10)
        progress_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.progress_text = tk.Text(progress_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        self.progress_text.pack(fill="both", expand=True)
        
        progress_scrollbar = ttk.Scrollbar(progress_frame, orient=tk.VERTICAL, command=self.progress_text.yview)
        progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.progress_text.config(yscrollcommand=progress_scrollbar.set)


    def add_files(self):
        files = filedialog.askopenfilenames(
            title="動画ファイルを選択",
            filetypes=(("MP4 files", "*.mp4"),
                       ("MOV files", "*.mov"),
                       ("AVI files", "*.avi"),
                       ("MKV files", "*.mkv"),
                       ("All files", "*.*"))
        )
        if files:
            for file in files:
                if file not in self.input_files:
                    self.input_files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
            self.update_log(f"{len(files)} 個のファイルを追加しました。")

    def remove_selected_files(self):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "削除するファイルを選択してください。")
            return
        
        # 後ろから削除しないとインデックスがずれる
        for index in reversed(selected_indices):
            self.file_listbox.delete(index)
            del self.input_files[index]
        self.update_log(f"{len(selected_indices)} 個のファイルをリストから削除しました。")


    def clear_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.input_files.clear()
        self.update_log("ファイルリストをクリアしました。")

    def select_output_directory(self):
        directory = filedialog.askdirectory(title="出力フォルダを選択")
        if directory:
            self.output_dir_var.set(directory)
            self.update_log(f"出力フォルダを設定: {directory}")

    def update_log(self, message, is_error=False):
        self.progress_text.config(state=tk.NORMAL)
        if is_error:
            self.progress_text.insert(tk.END, f"エラー: {message}\n", "error")
            self.progress_text.tag_config("error", foreground="red")
        else:
            self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END) # 自動スクロール
        self.progress_text.config(state=tk.DISABLED)
        self.root.update_idletasks() # GUIの更新を強制

    def start_compression_thread(self):
        if not self.input_files:
            messagebox.showerror("エラー", "圧縮するファイルが選択されていません。")
            return

        output_dir = self.output_dir_var.get()
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showerror("エラー", "有効な出力フォルダを指定してください。")
            return

        try:
            fps = int(self.fps_var.get())
            crf = int(self.crf_var.get())
        except ValueError:
            messagebox.showerror("エラー", "フレームレートとCRF値は数値で指定してください。")
            return
            
        audio_bitrate = self.audio_bitrate_var.get()

        self.compress_button.config(state=tk.DISABLED)
        self.update_log("圧縮処理を開始します...")

        # 圧縮処理を別スレッドで実行
        thread = threading.Thread(target=self.run_compression_batch,
                                  args=(list(self.input_files), output_dir, fps, crf, audio_bitrate), # リストのコピーを渡す
                                  daemon=True) # メインスレッド終了時にデーモンスレッドも終了
        thread.start()
        
    def run_compression_batch(self, files_to_process, output_dir, fps, crf, audio_bitrate):
        total_files = len(files_to_process)
        for i, input_file in enumerate(files_to_process):
            base, ext = os.path.splitext(os.path.basename(input_file))
            output_file = os.path.join(output_dir, f"{base}_compressed{ext}")

            self.update_log(f"--- [{i+1}/{total_files}] 処理中: {os.path.basename(input_file)} ---")
            
            try:
                original_size_mb = os.path.getsize(input_file) / (1024 * 1024)
                self.update_log(f"オリジナルサイズ: {original_size_mb:.2f} MB")
            except OSError:
                pass # サイズ取得失敗は無視

            success, message = self.compress_video_ffmpeg(input_file, output_file, fps, crf, audio_bitrate)
            
            if success:
                try:
                    compressed_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                    self.update_log(f"圧縮完了: {os.path.basename(output_file)} ({compressed_size_mb:.2f} MB)")
                except OSError:
                     self.update_log(f"圧縮完了: {os.path.basename(output_file)}")
            else:
                self.update_log(f"圧縮失敗: {os.path.basename(input_file)}. 詳細: {message}", is_error=True)
            self.update_log("-" * 30)

        self.update_log("全ての処理が完了しました。")
        self.root.after(0, lambda: self.compress_button.config(state=tk.NORMAL)) # GUIの更新はメインスレッドで


    def compress_video_ffmpeg(self, input_file, output_file, frame_rate, crf, audio_bitrate):
        command = [
            'ffmpeg',
            '-i', input_file,
            '-r', str(frame_rate),
            '-c:v', 'libx264',
            '-crf', str(crf),
            '-preset', 'medium', # medium, fast, faster, veryfast など。圧縮率と速度のバランス
        ]
        if audio_bitrate.lower() == 'copy':
            command.extend(['-c:a', 'copy'])
        else:
            command.extend(['-c:a', 'aac', '-b:a', audio_bitrate])
        
        command.extend(['-y', output_file])

        self.update_log(f"コマンド: {' '.join(command)}")

        try:
            # universal_newlines=True は text=True と同等, encodingは環境に合わせて
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                       universal_newlines=True, encoding='utf-8', errors='ignore')
            
            # FFmpegの出力をリアルタイムでログに流す（ stderr からの情報を表示 ）
            # stdout, stderr = process.communicate() # これだと全処理が終わるまで待つ
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.update_log(f"FFmpeg: {line.strip()}")
            
            return_code = process.wait() # プロセスの終了を待つ

            if return_code == 0:
                return True, f"正常に完了しました。"
            else:
                # stderrからのより詳細なエラーメッセージを取得するために再度communicateを呼ぶか、
                # またはPopen時に取得したstderrの全体を読む
                # ここでは、リアルタイムで表示したものが主となる。
                # 最後の数行のエラーが重要なら、それを別途取得する処理を追加できる。
                # stdout_final, stderr_final = process.communicate() # 再度呼ぶと既に閉じている可能性
                
                # 簡略化のため、リターンコードでの判断とする
                # より詳細なエラーはリアルタイムログで確認
                return False, f"FFmpegがエラーコード {return_code} で終了しました。"

        except FileNotFoundError:
            return False, "FFmpegが見つかりません。インストールとパス設定を確認してください。"
        except Exception as e:
            return False, f"予期せぬエラー: {str(e)}"


if __name__ == '__main__':
    root = tk.Tk()
    app = VideoCompressorApp(root)
    root.mainloop()
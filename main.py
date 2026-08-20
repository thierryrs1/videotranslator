import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import whisper
import edge_tts
import asyncio
import subprocess
import imageio_ffmpeg

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int((secs - int(secs)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millis:03d}"

ctk.set_appearance_mode("Light")  
ctk.set_default_color_theme("blue")  # Clean interface, similar to SAP Fiori concepts

class VideoTranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Video Translator & Dubber")
        self.geometry("600x400")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="white")
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="Video Translator", 
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color="#002D5A" # SAP style dark blue
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        self.desc_label = ctk.CTkLabel(
            self.main_frame, 
            text="Selecione um vídeo local para transcrever, traduzir e dublar para o Inglês.", 
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#333333"
        )
        self.desc_label.grid(row=1, column=0, padx=20, pady=(0, 15))
        
        self.voice_var = ctk.StringVar(value="Masculino (Guy)")
        self.voice_dropdown = ctk.CTkOptionMenu(
            self.main_frame,
            values=["Masculino (Guy)", "Masculino (Christopher)", "Feminino (Aria)", "Feminino (Jenny)"],
            variable=self.voice_var,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#0A6ED1"
        )
        self.voice_dropdown.grid(row=2, column=0, padx=20, pady=(0, 15))

        self.select_btn = ctk.CTkButton(
            self.main_frame, 
            text="Selecionar Vídeo", 
            command=self.select_video, 
            height=40, 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#0A6ED1",
            hover_color="#0854A0"
        )
        self.select_btn.grid(row=3, column=0, padx=20, pady=10)
        
        self.file_label = ctk.CTkLabel(
            self.main_frame, 
            text="Nenhum arquivo selecionado", 
            text_color="#666666",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.file_label.grid(row=4, column=0, padx=20, pady=5)
        
        self.process_btn = ctk.CTkButton(
            self.main_frame, 
            text="Processar Vídeo", 
            command=self.start_processing, 
            height=40, 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), 
            state="disabled",
            fg_color="#0A6ED1",
            hover_color="#0854A0"
        )
        self.process_btn.grid(row=5, column=0, padx=20, pady=20)
        
        self.status_label = ctk.CTkLabel(
            self.main_frame, 
            text="", 
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#002D5A"
        )
        self.status_label.grid(row=6, column=0, padx=20, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, mode="determinate")
        self.progress_bar.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() # Oculta inicialmente
        
        self.video_path = None

    def select_video(self):
        filepath = filedialog.askopenfilename(
            title="Selecione o Vídeo",
            filetypes=(("Arquivos de Vídeo", "*.mp4 *.avi *.mkv *.mov"), ("Todos os arquivos", "*.*"))
        )
        if filepath:
            self.video_path = filepath
            self.file_label.configure(text=os.path.basename(filepath), text_color="#000000")
            self.process_btn.configure(state="normal")
            
    def start_processing(self):
        if not self.video_path:
            return
            
        self.process_btn.configure(state="disabled")
        self.select_btn.configure(state="disabled")
        self.progress_bar.grid() # Mostra a barra de progresso
        self.progress_bar.set(0)
        self.update_progress(0, "Iniciando processamento...")
        
        threading.Thread(target=self.process_video, daemon=True).start()
        
    def process_video(self):
        try:
            output_dir = os.path.dirname(self.video_path)
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            audio_path = os.path.join(output_dir, f"{base_name}_temp_audio.wav")
            eng_audio_path = os.path.join(output_dir, f"{base_name}_eng_audio.mp3")
            srt_path = os.path.join(output_dir, f"temp_subs.srt")
            final_video_path = os.path.join(output_dir, f"{base_name}_dubbed.mp4")

            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()

            self.update_progress(0.1, "Extraindo áudio do vídeo...")
            try:
                subprocess.run([ffmpeg_cmd, "-y", "-i", self.video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", audio_path], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                raise Exception(f"Erro ao extrair áudio: {e.stderr}")
            
            self.update_progress(0.2, "Carregando modelo de IA (pode demorar no primeiro uso)...")
            model = whisper.load_model("base")
            
            self.update_progress(0.4, "Transcrevendo e gerando legendas...")
            result = model.transcribe(audio_path, task="translate")
            translated_text = result["text"]
            
            # Criar arquivo SRT para as legendas
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(result['segments'], start=1):
                    start = format_time(segment['start'])
                    end = format_time(segment['end'])
                    text = segment['text'].strip()
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
            
            self.update_progress(0.7, "Gerando áudio dublado...")
            voices = {
                "Masculino (Guy)": "en-US-GuyNeural",
                "Masculino (Christopher)": "en-US-ChristopherNeural",
                "Feminino (Aria)": "en-US-AriaNeural",
                "Feminino (Jenny)": "en-US-JennyNeural"
            }
            selected_voice = voices.get(self.voice_var.get(), "en-US-GuyNeural")
            
            communicate = edge_tts.Communicate(translated_text, selected_voice)
            asyncio.run(communicate.save(eng_audio_path))
            
            self.update_progress(0.9, "Juntando áudio e legendas ao vídeo...")
            
            # Usar ffmpeg para juntar vídeo, novo áudio e queimar a legenda na imagem
            srt_filename = os.path.basename(srt_path)
            cmd = [
                ffmpeg_cmd, "-y", 
                "-i", os.path.basename(self.video_path), 
                "-i", os.path.basename(eng_audio_path),
                "-c:v", "libx264", 
                "-c:a", "aac", 
                "-vf", f"subtitles={srt_filename}:force_style='FontSize=18,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=2,Shadow=0'",
                "-map", "0:v:0", "-map", "1:a:0",
                os.path.basename(final_video_path)
            ]
            
            try:
                subprocess.run(cmd, cwd=output_dir, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                raise Exception(f"Erro ao legendar vídeo: {e.stderr}")
            
            if os.path.exists(audio_path): os.remove(audio_path)
            if os.path.exists(eng_audio_path): os.remove(eng_audio_path)
            if os.path.exists(srt_path): os.remove(srt_path)
            
            self.update_progress(1.0, "Concluído! Vídeo salvo na mesma pasta.")
            messagebox.showinfo("Sucesso", f"Vídeo dublado salvo em:\n{final_video_path}")
            
        except Exception as e:
            self.update_progress(0, f"Erro: {str(e)}")
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{str(e)}\n\nLembre-se de ter o FFmpeg instalado.")
            
        finally:
            self.process_btn.configure(state="normal")
            self.select_btn.configure(state="normal")

    def update_progress(self, value, text):
        self.status_label.configure(text=text)
        self.progress_bar.set(value)

if __name__ == "__main__":
    app = VideoTranslatorApp()
    app.mainloop()

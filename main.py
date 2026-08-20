import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import whisper
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip

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
        self.desc_label.grid(row=1, column=0, padx=20, pady=(0, 30))
        
        self.select_btn = ctk.CTkButton(
            self.main_frame, 
            text="Selecionar Vídeo", 
            command=self.select_video, 
            height=40, 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#0A6ED1",
            hover_color="#0854A0"
        )
        self.select_btn.grid(row=2, column=0, padx=20, pady=10)
        
        self.file_label = ctk.CTkLabel(
            self.main_frame, 
            text="Nenhum arquivo selecionado", 
            text_color="#666666",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.file_label.grid(row=3, column=0, padx=20, pady=5)
        
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
        self.process_btn.grid(row=4, column=0, padx=20, pady=20)
        
        self.status_label = ctk.CTkLabel(
            self.main_frame, 
            text="", 
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#002D5A"
        )
        self.status_label.grid(row=5, column=0, padx=20, pady=10)
        
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
        self.status_label.configure(text="Iniciando processamento...")
        
        threading.Thread(target=self.process_video, daemon=True).start()
        
    def process_video(self):
        try:
            output_dir = os.path.dirname(self.video_path)
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            audio_path = os.path.join(output_dir, f"{base_name}_temp_audio.wav")
            eng_audio_path = os.path.join(output_dir, f"{base_name}_eng_audio.mp3")
            final_video_path = os.path.join(output_dir, f"{base_name}_dubbed.mp4")

            self.update_status("Extraindo áudio do vídeo...")
            video = VideoFileClip(self.video_path)
            video.audio.write_audiofile(audio_path, logger=None)
            
            self.update_status("Carregando modelo de IA (pode demorar no primeiro uso)...")
            model = whisper.load_model("base")
            
            self.update_status("Transcrevendo e traduzindo para o inglês...")
            result = model.transcribe(audio_path, task="translate")
            translated_text = result["text"]
            
            self.update_status("Gerando áudio dublado (Inglês)...")
            tts = gTTS(text=translated_text, lang='en', slow=False)
            tts.save(eng_audio_path)
            
            self.update_status("Juntando novo áudio com o vídeo...")
            new_audio = AudioFileClip(eng_audio_path)
            final_video = video.set_audio(new_audio)
            final_video.write_videofile(final_video_path, codec="libx264", audio_codec="aac", logger=None)
            
            video.close()
            final_video.close()
            new_audio.close()
            
            if os.path.exists(audio_path): os.remove(audio_path)
            if os.path.exists(eng_audio_path): os.remove(eng_audio_path)
            
            self.update_status("Concluído! Vídeo salvo na mesma pasta.")
            messagebox.showinfo("Sucesso", f"Vídeo dublado salvo em:\n{final_video_path}")
            
        except Exception as e:
            self.update_status(f"Erro: {str(e)}")
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{str(e)}\n\nLembre-se de ter o FFmpeg instalado.")
            
        finally:
            self.process_btn.configure(state="normal")
            self.select_btn.configure(state="normal")

    def update_status(self, text):
        self.status_label.configure(text=text)

if __name__ == "__main__":
    app = VideoTranslatorApp()
    app.mainloop()

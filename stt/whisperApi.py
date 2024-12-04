import whisper
import torch
import sounddevice as sd
import numpy as np
import queue
import threading
import time
import webrtcvad
import wave
import datetime

class AudioTranscriber:
    def __init__(self, model_name: str = "base", sample_rate: int = 16000):
        self.model = whisper.load_model(model_name)
        self.sample_rate = sample_rate
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()  # 텍스트 전달을 위한 큐 추가
        self.keep_running = True
        self.vad = webrtcvad.Vad(3)  # Aggressiveness mode 3
        self.buffer = []
        self.recording = False
        self.silence_threshold = 0.01
        self.silence_duration = 0
        self.max_silence_duration = 2.0  # 침묵 감지 시간을 2초로 증가
        self.transcription_callback: callable = None
        
    def start_streaming(self, callback: callable = None):
        """스트리밍 녹음을 시작합니다."""
        try:
            print("Starting audio streaming...")
            self.transcription_callback = callback
            self.buffer = []
            self.recording = True
            self.keep_running = True
            
            # 오디오 입력 스트림 시작
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
                dtype=np.float32
            )
            
            print("Opening audio stream...")
            self.stream.start()
            print("Audio stream started")
            
            # 처리 스레드 시작
            self.process_thread = threading.Thread(target=self.process_audio)
            self.process_thread.daemon = True
            self.process_thread.start()
            print("Processing thread started")
            
            # 콜백 처리 스레드 시작
            self.callback_thread = threading.Thread(target=self.handle_callbacks)
            self.callback_thread.daemon = True
            self.callback_thread.start()
            print("Callback thread started")
            
            return True
            
        except Exception as e:
            print(f"Error starting streaming: {str(e)}")
            self.keep_running = False
            self.recording = False
            raise
            
    def handle_callbacks(self):
        """콜백을 메인 스레드에서 처리하기 위한 함수"""
        while self.keep_running:
            try:
                text = self.text_queue.get(timeout=1.0)
                if self.transcription_callback and text:
                    self.transcription_callback(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in callback handler: {str(e)}")
                
    def process_audio(self):
        """오디오를 처리하고 텍스트로 변환하는 백그라운드 스레드"""
        while self.keep_running:
            try:
                # 침묵 감지
                if len(self.buffer) > 0:
                    audio_data = np.array(self.buffer, dtype=np.float32)
                    energy = np.mean(np.abs(audio_data))
                    
                    if energy < self.silence_threshold:
                        self.silence_duration += len(audio_data) / self.sample_rate
                        if self.silence_duration >= self.max_silence_duration:
                            # 현재까지의 버퍼를 처리
                            if len(self.buffer) > 0:
                                audio_data = np.array(self.buffer, dtype=np.float32)
                                try:
                                    result = self.model.transcribe(audio_data)
                                    transcribed_text = result["text"].strip()
                                    if transcribed_text:
                                        self.text_queue.put(transcribed_text)
                                        print(f"Transcribed: {transcribed_text}")
                                except Exception as e:
                                    print(f"Error in transcription: {str(e)}")
                            self.buffer = []
                            self.silence_duration = 0
                    else:
                        self.silence_duration = 0
                        
                time.sleep(0.1)  # CPU 사용량 감소
                    
            except Exception as e:
                print(f"Error in processing: {str(e)}")
                
    def stop_streaming(self):
        """스트리밍을 중지하고 마지막 텍스트를 반환합니다."""
        print("Stopping streaming...")
        if self.recording:
            self.keep_running = False
            self.recording = False
            self.stream.stop()
            self.stream.close()
            
            # 마지막 버퍼 처리
            if len(self.buffer) > 0:
                try:
                    audio_data = np.array(self.buffer, dtype=np.float32)
                    result = self.model.transcribe(audio_data)
                    transcribed_text = result["text"].strip()
                    print(f"Final transcription: {transcribed_text}")
                    return transcribed_text
                except Exception as e:
                    print(f"Error in final transcription: {str(e)}")
                finally:
                    self.buffer = []
            
        return None
        
    def audio_callback(self, indata, frames, time, status):
        """오디오 입력 콜백"""
        if status:
            print(f'Audio callback status: {status}')
            return
            
        if self.recording:
            try:
                # 오디오 데이터를 float32로 변환
                audio_data = indata.flatten().astype(np.float32)
                
                # 오디오 큐에 데이터 추가
                self.buffer.extend(audio_data.tolist())
                
                # 디버그: 오디오 레벨 출력
                energy = np.mean(np.abs(audio_data))
                if energy > self.silence_threshold:
                    print(f"Audio level: {energy:.4f}")
                    
            except Exception as e:
                print(f"Error in audio callback: {str(e)}")
                
    def save_audio(self, audio_data, filename):
        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

    def record_and_transcribe(self, duration=5):
        """Record audio and transcribe it using Whisper"""
        print("녹음을 시작합니다...")
        
        # Initialize recording
        self.buffer = []
        self.recording = False
        self.silence_duration = 0
        
        # Start recording
        with sd.InputStream(callback=self.audio_callback,
                          channels=1,
                          samplerate=self.sample_rate):
            try:
                # Record for specified duration
                time.sleep(duration)
                
                # Convert buffer to numpy array
                if self.buffer:
                    audio_data = np.array(self.buffer, dtype=np.float32)
                    
                    # Transcribe using Whisper
                    result = self.model.transcribe(audio_data)
                    transcribed_text = result["text"].strip()
                    
                    print("변환된 텍스트:", transcribed_text)
                    return transcribed_text
                else:
                    print("음성이 감지되지 않았습니다.")
                    return None
                    
            except Exception as e:
                print(f"녹음 중 오류 발생: {str(e)}")
                return None

    def transcribe(self, audio_path):
        """
        오디오 파일을 텍스트로 변환합니다.
        
        Args:
            audio_path (str): 오디오 파일 경로
            
        Returns:
            str: 변환된 텍스트
        """
        try:
            print(f"Transcribing audio file: {audio_path}")
            
            # Load audio file using whisper's built-in audio loading
            result = self.model.transcribe(audio_path, language="ko")
            transcribed_text = result["text"].strip()
            
            print(f"Transcription result: {transcribed_text}")
            return transcribed_text
            
        except Exception as e:
            print(f"Error in transcription: {str(e)}")
            return None
            
def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    def transcription_callback(text):
        print(f"Transcription: {text}")
        
    transcriber = AudioTranscriber(model_name="base")
    transcriber.start_streaming(callback=transcription_callback)
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        transcriber.stop_streaming()

if __name__ == "__main__":
    main()
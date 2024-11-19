import os
from gtts import gTTS
from io import BytesIO
from pydub import AudioSegment
from pydub.playback import play
import speech_recognition as sr
from IPython.display import Audio
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st
import datetime

# Path to store voice files
path = "../data/voice/"
os.makedirs(path, exist_ok=True)

# 1. Save and play voice created by Google Text-to-Speech (gTTS)
def text_to_audio(text, filename):
    tts = gTTS(text)
    file_path = os.path.join(path, filename)
    tts.save(file_path)
    return file_path

def play_audio(file_path):
    audio = AudioSegment.from_file(file_path)
    play(audio)

# 2. Use microphone to record voice
def record_audio(duration=5, save_file=True):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("주변 소음을 측정 중...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"{duration}초 동안 녹음합니다...")
        try:
            recorded_audio = recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
            print("녹음 완료.")
            
            if save_file:
                # WAV 파일로 저장
                import wave
                audio_data = recorded_audio.get_wav_data()
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(path, f"recorded_{timestamp}.wav")
                
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(1)  # 모노 채널
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(44100)  # 샘플레이트
                    wf.writeframes(audio_data)
                print(f"녹음 파일이 저장되었습니다: {filename}")
            
            return recorded_audio
        except sr.WaitTimeoutError:
            print("타임아웃: 음성이 감지되지 않았습니다.")
            return None

# 3. Convert the recorded voice to text through speech-to-text (STT)
def audio_to_text(audio):
    recognizer = sr.Recognizer()
    try:
        print("Recognizing the text...")
        text = recognizer.recognize_google(audio, language="en-US")
        print("Decoded Text: {}".format(text))
    except sr.UnknownValueError:
        text = "Google Speech Recognition could not understand the audio."
    except sr.RequestError:
        text = "Could not request results from Google Speech Recognition service."
    return text

# 4. Convert the text to voice through text-to-speech (TTS)
def text_to_speech(text):
    tts = gTTS(text)
    audio_buffer = BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    audio_segment = AudioSegment.from_file(audio_buffer, format="mp3")
    play(audio_segment)

# 5. Make a voice-to-voice stream
def voice_to_voice():
    recorded_audio = record_audio()
    if recorded_audio is None:
        return
    text = audio_to_text(recorded_audio)
    text_to_speech(text)

# 6. Integrate an LLM to respond to voice input with voice output
load_dotenv()
GOOGLE_API_KEY = os.getenv("GCP_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
gemini_pro = genai.GenerativeModel(model_name="models/gemini-pro")

def respond_by_gemini(input_text, role_text, instructions_text):
    final_prompt = [
        "ROLE: " + role_text,
        "INPUT_TEXT: " + input_text,
        instructions_text,
    ]
    response = gemini_pro.generate_content(
        final_prompt,
        stream=True,
    )
    response_list = []
    for chunk in response:
        response_list.append(chunk.text)
    response_text = "".join(response_list)
    return response_text

def llm_voice_response():
    role = 'You are an intelligent assistant to chat on the topic: `{}`.'
    topic = 'The future of artificial intelligence'
    role_text = role.format(topic)
    instructions = 'Respond to the INPUT_TEXT briefly in chat style. Respond based on your knowledge about `{}` in brief chat style.'
    instructions_text = instructions.format(topic)
    
    recorded_audio = record_audio()
    if recorded_audio is None:
        return
    text = audio_to_text(recorded_audio)
    response_text = text
    if text not in ["Google Speech Recognition could not understand the audio.", "Could not request results from Google Speech Recognition service."]:
        response_text = respond_by_gemini(text, role_text, instructions_text)
    text_to_speech(response_text)

# 7. Build a Web interface for the LLM-supported voice assistant
def test_microphone():
    print("마이크 테스트를 시작합니다...")
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("마이크가 감지되었습니다.")
            print("사용 가능한 마이크:", sr.Microphone.list_microphone_names())
            print("잠시 후 음성을 녹음합니다...")
            r.adjust_for_ambient_noise(source, duration=1)
            print("녹음을 시작합니다. 아무 말이나 해보세요.")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=5)
                print("녹음이 완료되었습니다.")
                try:
                    text = r.recognize_google(audio, language="ko-KR")
                    print("인식된 텍스트:", text)
                except sr.UnknownValueError:
                    print("음성을 인식할 수 없습니다.")
                except sr.RequestError as e:
                    print("Google Speech Recognition 서비스 에러:", str(e))
            except sr.WaitTimeoutError:
                print("타임아웃: 음성이 감지되지 않았습니다.")
    except Exception as e:
        print("마이크 초기화 중 에러 발생:", str(e))

def main():
    # Streamlit setup with custom CSS
    st.set_page_config(page_title="LLM-Supported Voice Assistant", layout="wide")
    
    st.markdown("""
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .main {background-color: #f5f5f5;}
            .container {max-width: 800px; margin: auto; padding-top: 50px;}
            .title {font-family: 'Arial', sans-serif; color: #333333; margin-bottom: 30px;}
            .btn {background-color: #4CAF50; color: white; border: none; padding: 10px 20px; cursor: pointer; font-size: 16px;}
            .btn:hover {background-color: #45a049;}
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='container'><h1 class='title'>LLM-Supported Voice Assistant</h1></div>", unsafe_allow_html=True)
    
    st.write("This is a voice assistant with LLM support. Speak to the microphone, and the assistant will respond.")
    
    if st.button("Record and Get Response", key="record_btn"):
        st.write("Listening...")
        llm_voice_response()
        st.write("Done.")
    
    if st.button("Test Microphone", key="test_microphone_btn"):
        st.write("Testing microphone...")
        test_microphone()
        st.write("Done.")
    
    st.markdown("<div class='container'><h5>Press the button and speak to the microphone. The assistant will generate a response based on the input and speak it out loud.</h5></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
import os
from gtts import gTTS
from io import BytesIO
from pydub import AudioSegment
from pydub.playback import play
import speech_recognition as sr
from IPython.display import Audio
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st
import datetime

# Path to store voice files
path = "../data/voice/"
os.makedirs(path, exist_ok=True)

# 1. Save and play voice created by Google Text-to-Speech (gTTS)
def text_to_audio(text, filename):
    tts = gTTS(text)
    file_path = os.path.join(path, filename)
    tts.save(file_path)
    return file_path

def play_audio(file_path):
    audio = AudioSegment.from_file(file_path)
    play(audio)

# 2. Use microphone to record voice
def record_audio(duration=5, save_file=True):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("주변 소음을 측정 중...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"{duration}초 동안 녹음합니다...")
        try:
            recorded_audio = recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
            print("녹음 완료.")
            
            if save_file:
                # WAV 파일로 저장
                import wave
                audio_data = recorded_audio.get_wav_data()
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(path, f"recorded_{timestamp}.wav")
                
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(1)  # 모노 채널
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(44100)  # 샘플레이트
                    wf.writeframes(audio_data)
                print(f"녹음 파일이 저장되었습니다: {filename}")
            
            return recorded_audio
        except sr.WaitTimeoutError:
            print("타임아웃: 음성이 감지되지 않았습니다.")
            return None

# 3. Convert the recorded voice to text through speech-to-text (STT)
def audio_to_text(audio):
    recognizer = sr.Recognizer()
    try:
        print("Recognizing the text...")
        text = recognizer.recognize_google(audio, language="en-US")
        print("Decoded Text: {}".format(text))
    except sr.UnknownValueError:
        text = "Google Speech Recognition could not understand the audio."
    except sr.RequestError:
        text = "Could not request results from Google Speech Recognition service."
    return text

# 4. Convert the text to voice through text-to-speech (TTS)
def text_to_speech(text):
    tts = gTTS(text)
    audio_buffer = BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    audio_segment = AudioSegment.from_file(audio_buffer, format="mp3")
    play(audio_segment)

# 5. Make a voice-to-voice stream
def voice_to_voice():
    recorded_audio = record_audio()
    if recorded_audio is None:
        return
    text = audio_to_text(recorded_audio)
    text_to_speech(text)

# 6. Integrate an LLM to respond to voice input with voice output
load_dotenv()
GOOGLE_API_KEY = os.getenv("GCP_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
gemini_pro = genai.GenerativeModel(model_name="models/gemini-pro")

def respond_by_gemini(input_text, role_text, instructions_text):
    final_prompt = [
        "ROLE: " + role_text,
        "INPUT_TEXT: " + input_text,
        instructions_text,
    ]
    response = gemini_pro.generate_content(
        final_prompt,
        stream=True,
    )
    response_list = []
    for chunk in response:
        response_list.append(chunk.text)
    response_text = "".join(response_list)
    return response_text

def llm_voice_response():
    role = 'You are an intelligent assistant to chat on the topic: `{}`.'
    topic = 'The future of artificial intelligence'
    role_text = role.format(topic)
    instructions = 'Respond to the INPUT_TEXT briefly in chat style. Respond based on your knowledge about `{}` in brief chat style.'
    instructions_text = instructions.format(topic)
    
    recorded_audio = record_audio()
    if recorded_audio is None:
        return
    text = audio_to_text(recorded_audio)
    response_text = text
    if text not in ["Google Speech Recognition could not understand the audio.", "Could not request results from Google Speech Recognition service."]:
        response_text = respond_by_gemini(text, role_text, instructions_text)
    text_to_speech(response_text)

# 7. Build a Web interface for the LLM-supported voice assistant
def test_microphone():
    print("마이크 테스트를 시작합니다...")
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("마이크가 감지되었습니다.")
            print("사용 가능한 마이크:", sr.Microphone.list_microphone_names())
            print("잠시 후 음성을 녹음합니다...")
            r.adjust_for_ambient_noise(source, duration=1)
            print("녹음을 시작합니다. 아무 말이나 해보세요.")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=5)
                print("녹음이 완료되었습니다.")
                try:
                    text = r.recognize_google(audio, language="ko-KR")
                    print("인식된 텍스트:", text)
                except sr.UnknownValueError:
                    print("음성을 인식할 수 없습니다.")
                except sr.RequestError as e:
                    print("Google Speech Recognition 서비스 에러:", str(e))
            except sr.WaitTimeoutError:
                print("타임아웃: 음성이 감지되지 않았습니다.")
    except Exception as e:
        print("마이크 초기화 중 에러 발생:", str(e))

def main():
    # Streamlit setup with custom CSS
    st.set_page_config(page_title="LLM-Supported Voice Assistant", layout="wide")
    
    st.markdown("""
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .main {background-color: #f5f5f5;}
            .container {max-width: 800px; margin: auto; padding-top: 50px;}
            .title {font-family: 'Arial', sans-serif; color: #333333; margin-bottom: 30px;}
            .btn {background-color: #4CAF50; color: white; border: none; padding: 10px 20px; cursor: pointer; font-size: 16px;}
            .btn:hover {background-color: #45a049;}
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='container'><h1 class='title'>LLM-Supported Voice Assistant</h1></div>", unsafe_allow_html=True)
    
    st.write("This is a voice assistant with LLM support. Speak to the microphone, and the assistant will respond.")
    
    if st.button("Record and Get Response", key="record_btn"):
        st.write("Listening...")
        llm_voice_response()
        st.write("Done.")
    
    if st.button("Test Microphone", key="test_microphone_btn"):
        st.write("Testing microphone...")
        test_microphone()
        st.write("Done.")
    
    st.markdown("<div class='container'><h5>Press the button and speak to the microphone. The assistant will generate a response based on the input and speak it out loud.</h5></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()


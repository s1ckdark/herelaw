import streamlit as st
import speech_recognition as sr
import pyttsx3


def main():
    st.title("음성 대화 챗봇")

    # 음성 입력을 위한 함수
    def get_audio_input():
        r = sr.Recognizer()

        with sr.Microphone() as source:
            audio = r.listen(source)

        # 구글 웹 음성 API로 인식하기 
        try:
            print("Google Speech Recognition thinks you said : " + r.recognize_google(audio, language='ko'))
            return r.recognize_google(audio, language='ko')
        except sr.UnknownValueError as e:
            print("Google Speech Recognition could not understand audio".format(e))
            return None
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))
            return None


    # 챗봇 응답을 얻는 함수
    def get_chatbot_response(user_input):
        # 여기에서 실제로 챗봇의 응답 로직을 구현할 수 있습니다.
        return f"챗봇: '{user_input}'에 대한 답변입니다."

    user_input = st.text_input("사용자 음성 입력:")

    # TTS 
    def text_to_speech(text):
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    

    if st.button("마이크 켜기"):
        user_input = get_audio_input()
        if user_input is not None:
            st.text(f"사용자: {user_input}")
            chatbot_response = get_chatbot_response(user_input)
            st.text(chatbot_response)    
            # TTS api
            text_to_speech(chatbot_response)

if __name__ == "__main__":
    main()
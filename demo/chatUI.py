import streamlit as st 
import time 
import random 
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import os 
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Your Chat App", page_icon=":speech_balloon:")
st.title("🚀 AI Chatterbox: Your Interactive Conversation Partner 🗨️")
# Get API Key from .env file

# Load the model from OpenAI's API and create a chat object with it
chat=ChatOpenAI(model="gpt-3.5-turbo",temperature=0.0,api_key=os.getenv("OPENAI_API_KEY"))

memoryforchat=ConversationBufferMemory()
convo=ConversationChain(memory=memoryforchat,llm=chat,verbose=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history=[]
else:
    for message in st.session_state.chat_history:
        memoryforchat.save_context({"input":message["human"]},{"outputs":message["AI"]})

if "message" not in st.session_state:
    st.session_state.message = [{"role":"assistant","content":"how may i help you "}]
for message1 in st.session_state.message:
    with st.chat_message(message1["role"]):
        st.markdown(message1["content"])

if prompt:=st.chat_input("Say Something"):
        with st.chat_message("user"):
            st.markdown(prompt)
            st.session_state.message.append({"role":"user","content":prompt})
            
        with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    time.sleep(1)
                    responce=convo.predict(input=prompt)
                    st.write(responce)
        st.session_state.message.append({"role":"assistant","content":responce})
        message={'human':prompt,"AI":responce}
        st.session_state.chat_history.append(message)

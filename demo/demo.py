import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai.llms import OpenAI
from dotenv import load_dotenv
import os

# .env 파일에서 API 키 로드
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Streamlit 페이지 설정
st.set_page_config(page_title="Legal Advisor", page_icon="⚖️")
st.title("🚀 AI Legal Advisor: Get Your Case Evaluated 🗨️")

# 사용자로부터 질문 입력받기
user_question = st.text_area("Enter the details of your legal case:")

# 템플릿 정의
template = """당신의 임무는 변호사로서 {question}를 처리하는 것입니다. 케이스에 대한 항목을 분류해서 답해주세요"""

# LLM 객체 생성
llm = OpenAI(
    model_name="ft:gpt-4o-mini-2024-07-18:personal::A16MtkYX",  # 모델명
    temperature=0,  # 창의성 조절
    api_key=api_key
)

# 프롬프트 템플릿 설정
chat_prompt = PromptTemplate(
    input_variables=["question"],
    template=template
)

# LLMChain 생성
llm_chain = LLMChain(llm=llm, prompt=chat_prompt)

# 버튼 클릭 시 응답 생성
if st.button("Get Legal Advice"):
    if user_question:
        with st.spinner("Analyzing your case..."):
            response = llm_chain.run(question=user_question)
            st.write("### AI's Response:")
            st.write(response)
    else:
        st.warning("Please enter the details of your legal case.")

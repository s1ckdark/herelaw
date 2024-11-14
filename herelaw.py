import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from dotenv import load_dotenv
import os

# .env 파일에서 API 키 로드
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Streamlit 페이지 설정
st.set_page_config(page_title="Herelaw", page_icon="⚖️")
st.title("🚀 Herelaw AI Legal Assistant")

# 사용자로부터 질문 입력받기
user_question = st.text_area("Enter the details of your legal case:")

# "소장을 작성해줘" 문구 추가
user_question_request = user_question + "이 사건에 대해 법원 제출할 소장 초안을 작성해줘."

# 템플릿 정의
template = """당신의 임무는 변호사로서 {question}를 처리하는 것입니다. 케이스에 대한 항목을 분류하고 분석해주세요"""

# GPT-4o-mini 모델 생성
gpt4_mini_llm = ChatOpenAI(
    model_name="gpt-4o-mini",  # GPT-4o-mini 모델
    temperature=0,
    api_key=api_key
)

# 파인튜닝된 모델 생성
fine_tuned_llm = ChatOpenAI(
    model_name="ft:gpt-4o-mini-2024-07-18:personal::A16MtkYX",  # 파인튜닝된 모델 ID
    temperature=0,
    api_key=api_key
)

# 프롬프트 템플릿 설정
chat_prompt = PromptTemplate(
    input_variables=["question"],
    template=template
)

# 두 개의 LLMChain 생성
gpt4_mini_chain = LLMChain(llm=gpt4_mini_llm, prompt=chat_prompt)
fine_tuned_chain = LLMChain(llm=fine_tuned_llm, prompt=chat_prompt)

# Langsmith Traceable Wrappers
traceable_gpt4_mini = traceable(gpt4_mini_chain)
traceable_fine_tuned = traceable(fine_tuned_chain)

# 버튼 클릭 시 응답 생성
if st.button("케이스 분석하기"):
    if user_question:
        with st.spinner("Analyzing your case..."):
            # 두 모델로부터 답변 받기
            gpt4_mini_response = gpt4_mini_chain.run(question=user_question)
            fine_tuned_response = fine_tuned_chain.run(question=user_question)

            # 소장 작성 요청 처리
            export_response = gpt4_mini_chain.run(question=user_question_request)

            # 종합 답변 생성
            combined_response = f"**파인튜닝된 모델의 답변:**\n{fine_tuned_response}\n\n" \
                                f"**소장 작성:**\n{export_response}"

            # 결과 출력
            st.write(combined_response)

    else:
        st.warning("Please enter the details of your legal case.")
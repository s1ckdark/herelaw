import openai
import json
from docx import Document
from dotenv import load_dotenv
import os
from typing import Dict, Any

class DivorceComplaintGenerator:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=openai.api_key)
        # JSON 템플릿 로드
        with open('complaint_template.json', 'r', encoding='utf-8') as f:
            self.template = json.load(f)

    def read_dialog_from_docx(self, file_path: str) -> str:
        """docx 파일에서 대화 내용 읽기"""
        doc = Document(file_path)
        dialog_text = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
        return '\n'.join(dialog_text)

    def fill_template_with_gpt(self, dialog_text: str) -> Dict[str, Any]:
        """GPT-4 API를 사용하여 대화 내용에서 정보를 추출하고 템플릿을 채웁니다."""
        
        system_message = """
        아래 템플릿에 맞추어 JSON 데이터를 채워주세요.
        사용자가 제공한 대화 내용을 바탕으로 필드 값을 추출하고, 가능하면 정확한 데이터를 입력하세요.
        값이 없는 경우 None을 사용해 JSON 형식을 준수하세요.
        """
        
        prompt = f"대화 내용: {dialog_text}\n\n템플릿: {json.dumps(self.template, ensure_ascii=False)}"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
            )
            
            # GPT-4 API 응답을 JSON 형식으로 파싱
            content = response.choices[0].message.content.strip()
            filled_data = json.loads(content)
            return filled_data
        
        except json.JSONDecodeError as e:
            print("JSON 디코딩 오류:", e)
            return None
        except openai.OpenAIError as e:
            print("OpenAI API 요청 오류:", e)
            return None

    def save_template_as_json(self, data: Dict[str, Any], output_path: str):
        """채워진 템플릿을 JSON 파일로 저장합니다."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"채워진 JSON 템플릿이 '{output_path}'에 저장되었습니다.")

def main():
    generator = DivorceComplaintGenerator()
    
    # data.docx 파일의 대화 내용 읽기
    dialog_path = "data.docx"
    dialog_text = generator.read_dialog_from_docx(dialog_path)
    
    # GPT-4 API를 사용하여 템플릿을 채우기
    filled_template = generator.fill_template_with_gpt(dialog_text)
    
    # 결과를 JSON 파일로 저장
    if filled_template:
        output_path = "filled_complaint_template.json"
        generator.save_template_as_json(filled_template, output_path)
    else:
        print("GPT-4로부터 데이터를 채우는 데 실패했습니다.")

if __name__ == "__main__":
    main()

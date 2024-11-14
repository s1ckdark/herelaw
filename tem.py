from typing import Dict, Any
import json
import openai
import os
from datetime import datetime
from docx import Document
import os
from dotenv import load_dotenv

class DivorceComplaintGenerator:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        
        # 기본 템플릿 로드
        with open('complaint_template.json', 'r', encoding='utf-8') as f:
            self.template = json.load(f)
            
    def read_dialog_from_docx(self, file_path: str) -> str:
        """docx 파일에서 대화 내용 읽기"""
        try:
            doc = Document(file_path)
            dialog_text = []
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:  # 빈 줄 제외
                    dialog_text.append(text)
                    
            return '\n'.join(dialog_text)
            
        except Exception as e:
            raise Exception(f"대화 파일 읽기 실패: {str(e)}")

    def extract_information_from_dialog(self, dialog_text: str) -> Dict[str, Any]:
      """OpenAI API를 사용하여 대화에서 정보 추출"""
      
      system_prompt = """
      다음 대화에서 이혼 소장 작성에 필요한 정보를 추출하여 JSON 형식으로 반환하세요.
      
      추출해야 할 정보와 JSON 형식:
      {
          "소장": {
              "기본정보": {
                  "사건명": "이혼 및 위자료 등 청구의 소",
                  "법원명": null,
                  "작성일자": null
              },
              "당사자": {
                  "원고": {
                      "성명": null,
                      "주민등록번호": null,
                      "등록기준지": null,
                      "주소": null,
                      "우편번호": null
                  },
                  "원고대리인": {
                      "유형": "변호사",
                      "성명": null,
                      "사무소명": null,
                      "주소": null,
                      "연락처": {
                          "전화": null,
                          "팩스": null
                      }
                  },
                  "피고": [
                      {
                          "순번": 1,
                          "성명": null,
                          "주민등록번호": null,
                          "등록기준지": null,
                          "주소": null,
                          "우편번호": null
                      }
                  ],
                  "사건본인": [
                      {
                          "순번": null,
                          "성명": null,
                          "주민등록번호": null,
                          "등록기준지": null,
                          "주소": null
                      }
                  ]
              },
              "청구취지": {
                  "이혼청구": {
                      "청구여부": false
                  },
                  "위자료": {
                      "청구여부": false,
                      "청구금액": null,
                      "이자": {
                          "이율": null,
                          "기산점": "소장부본송달일 다음날",
                          "종료점": "변제일"
                      },
                      "연대책임여부": false
                  },
                  "재산분할": {
                      "청구여부": false,
                      "청구금액": null,
                      "이자": {
                          "이율": null,
                          "기산점": "판결확정일 다음날",
                          "종료점": "변제일"
                      }
                  },
                  "친권자지정": {
                      "청구여부": false,
                      "지정대상자": null
                  },
                  "양육자지정": {
                      "청구여부": false,
                      "지정대상자": null
                  },
                  "양육비": {
                      "청구여부": false,
                      "지급의무자": null,
                      "자녀별내역": [
                          {
                              "자녀순번": null,
                              "월지급액": null,
                              "지급기간": {
                                  "시작일": "소장부본송달일 다음날",
                                  "종료일": null
                              }
                          }
                      ],
                      "지급일": "매월 말일"
                  }
              },
              "청구원인": {
                  "당사자관계": {
                      "혼인관계": {
                          "혼인신고일": null,
                          "혼인기간": null,
                          "자녀수": null
                      }
                  },
                  "이혼사유": {
                      "법적근거": {
                          "법률": "민법",
                          "조문": "제840조",
                          "호": null
                      },
                      "사유내용": []
                  }
              },
              "입증방법": {
                  "필수서류": {
                      "혼인관계증명서": {
                          "제출여부": false,
                          "문서번호": null
                      },
                      "가족관계증명서": {
                          "제출여부": false,
                          "문서번호": null
                      }
                  },
                  "기타증거": []
              }
          }
      }

      대화 내용을 분석하여 위 JSON 형식에 맞게 정보를 추출하세요.
      모든 금액은 숫자로 변환하여 입력하세요. (예: 5000만원 -> 50000000)
      날짜는 'YYYY년 MM월 DD일' 형식으로 입력하세요.
      알 수 없는 정보는 null로 유지하세요.
      """

      response = self.client.chat.completions.create(
          model="gpt-4o",
          messages=[
              {"role": "system", "content": system_prompt},
              {"role": "user", "content": dialog_text}
          ],
          temperature=0,
          response_format={"type": "json_object"}
      )
      
      try:
          extracted_data = json.loads(response.choices[0].message.content)
          print("추출된 데이터:")
          print(json.dumps(extracted_data, ensure_ascii=False, indent=2))
          return extracted_data
      except json.JSONDecodeError as e:
          print(f"JSON 파싱 오류: {str(e)}")
          print("원본 응답:", response.choices[0].message.content)
          raise

    def generate_complaint_from_template(self, dialog_file_path: str) -> Dict[str, Any]:
        """대화 내용을 바탕으로 소장 템플릿 생성"""
        
        # docx 파일에서 대화 읽기
        dialog_text = self.read_dialog_from_docx(dialog_file_path)
        
        # 대화에서 정보 추출
        extracted_data = self.extract_information_from_dialog(dialog_text)
        
        # 템플릿에 정보 매핑
        complaint_data = self.template.copy()
        
        # 기본정보 매핑
        complaint_data["소장"]["기본정보"].update({
            "사건명": "이혼 및 위자료 등 청구의 소",
            "작성일자": datetime.now().strftime("%Y년 %m월 %d일")
        })
        
        # 당사자 정보 매핑
        if extracted_data.get("당사자"):
            # 원고 정보
            if extracted_data["당사자"].get("원고"):
                complaint_data["소장"]["당사자"]["원고"].update(
                    extracted_data["당사자"]["원고"]
                )
            
            # 원고대리인 정보
            if extracted_data["당사자"].get("원고대리인"):
                complaint_data["소장"]["당사자"]["원고대리인"].update(
                    extracted_data["당사자"]["원고대리인"]
                )
            
            # 피고 정보
            if extracted_data["당사자"].get("피고"):
                complaint_data["소장"]["당사자"]["피고"] = []
                for idx, defendant in enumerate(extracted_data["당사자"]["피고"]):
                    defendant_data = {
                        "순번": idx + 1,
                        "성명": defendant.get("성명"),
                        "주민등록번호": defendant.get("주민등록번호"),
                        "등록기준지": defendant.get("등록기준지"),
                        "주소": defendant.get("주소"),
                        "우편번호": defendant.get("우편번호")
                    }
                    complaint_data["소장"]["당사자"]["피고"].append(defendant_data)
            
            # 사건본인 정보
            if extracted_data["당사자"].get("사건본인"):
                complaint_data["소장"]["당사자"]["사건본인"] = []
                for idx, person in enumerate(extracted_data["당사자"]["사건본인"]):
                    person_data = {
                        "순번": idx + 1,
                        "성명": person.get("성명"),
                        "주민등록번호": person.get("주민등록번호"),
                        "등록기준지": person.get("등록기준지"),
                        "주소": person.get("주소")
                    }
                    complaint_data["소장"]["당사자"]["사건본인"].append(person_data)
        
        # 청구취지 매핑
        if extracted_data.get("청구사항"):
            청구사항 = extracted_data["청구사항"]
            
            # 이혼청구
            if 청구사항.get("이혼청구"):
                complaint_data["소장"]["청구취지"]["이혼청구"].update(청구사항["이혼청구"])
            
            # 위자료
            if 청구사항.get("위자료"):
                complaint_data["소장"]["청구취지"]["위자료"].update({
                    "청구여부": True,
                    "청구금액": 청구사항["위자료"].get("청구금액"),
                    "이자": {
                        "이율": 청구사항["위자료"].get("이자율", 12),
                        "기산점": "소장부본송달일 다음날",
                        "종료점": "변제일"
                    },
                    "연대책임여부": 청구사항["위자료"].get("연대책임여부", False)
                })
            
            # 재산분할
            if 청구사항.get("재산분할"):
                complaint_data["소장"]["청구취지"]["재산분할"].update({
                    "청구여부": True,
                    "청구금액": 청구사항["재산분할"].get("청구금액"),
                    "이자": {
                        "이율": 청구사항["재산분할"].get("이자율", 5),
                        "기산점": "판결확정일 다음날",
                        "종료점": "변제일"
                    }
                })
            
            # 친권자지정
            if 청구사항.get("친권자지정"):
                complaint_data["소장"]["청구취지"]["친권자지정"].update(청구사항["친권자지정"])
                
            # 양육비
            if 청구사항.get("양육비"):
                complaint_data["소장"]["청구취지"]["양육비"].update({
                    "청구여부": True,
                    "지급의무자": 청구사항["양육비"].get("지급의무자"),
                    "자녀별내역": 청구사항["양육비"].get("자녀별내역", [])
                })
        
        # 청구원인 매핑
        if extracted_data.get("청구원인"):
            청구원인 = extracted_data["청구원인"]
            
            # 당사자관계
            if 청구원인.get("혼인관계"):
                complaint_data["소장"]["청구원인"]["당사자관계"]["혼인관계"].update(
                    청구원인["혼인관계"]
                )
            
            # 이혼사유
            if 청구원인.get("이혼사유"):
                complaint_data["소장"]["청구원인"]["이혼사유"]["사유내용"].append(
                    청구원인["이혼사유"]
                )
        
        # 입증방법 매핑
        if extracted_data.get("입증방법"):
            if extracted_data["입증방법"].get("필수서류"):
                complaint_data["소장"]["입증방법"]["필수서류"].update(
                    extracted_data["입증방법"]["필수서류"]
                )
            
            if extracted_data["입증방법"].get("기타증거"):
                complaint_data["소장"]["입증방법"]["기타증거"].extend(
                    extracted_data["입증방법"]["기타증거"]
                )
        
        return complaint_data

    def generate_complaint_text(self, complaint_data: Dict[str, Any]) -> str:
        """소장 데이터를 텍스트로 변환"""
        
        system_prompt = """
        다음 JSON 데이터를 바탕으로 이혼 소장을 작성하세요.
        
        작성 규칙:
        1. 법적 형식을 준수할 것
        2. 각 섹션(청구취지, 청구원인 등)을 명확히 구분할 것
        3. 누락된 정보는 포함하지 않을 것
        4. 공식적이고 격식 있는 문체를 사용할 것
        """

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(complaint_data, ensure_ascii=False)}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content

def main():
    # OpenAI API 키 설정
    api_key = os.getenv("HERELAW_OPENAI_API_KEY")
  
    # 소장 생성기 초기화
    generator = DivorceComplaintGenerator(api_key)
   
    # 대화 파일 경로
    dialog_file_path = "data.docx"
    
    try:
        # 소장 데이터 생성
        complaint_data = generator.generate_complaint_from_template(dialog_file_path)
    
        # 소장 텍스트 생성
        complaint_text = generator.generate_complaint_text(complaint_data)
        
        # 결과 출력
        print("=== 생성된 소장 ===")
       
        print("\n=== 추출된 데이터 ===")
        print(json.dumps(complaint_data, ensure_ascii=False, indent=2))
        
        # 결과 파일 저장
        with open('generated_complaint.txt', 'w', encoding='utf-8') as f:
            f.write(complaint_text)
            
        with open('extracted_data.json', 'w', encoding='utf-8') as f:
            json.dump(complaint_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    main()






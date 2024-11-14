import os
from docx import Document
import pandas as pd

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def process_docx_files(directory):
    cases = {}
    complaints = {}
    
    for filename in os.listdir(directory):
        if filename.endswith('.docx'):
            file_path = os.path.join(directory, filename)
            text = extract_text_from_docx(file_path)
            
            # 파일명에서 케이스 번호 추출 (예: "case_001" 또는 "complaint_001")
            case_number = filename.split('_')[1].split('.')[0]
            
            if filename.startswith('case'):
                cases[case_number] = text
            elif filename.startswith('complaint'):
                complaints[case_number] = text

    return cases, complaints

def create_dataset(cases, complaints):
    dataset = []
    
    for case_number in cases.keys():
        if case_number in complaints:
            dataset.append({
                'case_number': case_number,
                'case_text': cases[case_number],
                'complaint_text': complaints[case_number]
            })
        else:
            print(f"Warning: No matching complaint found for case {case_number}")
    
    return dataset

# 메인 실행 코드
directory = 'path/to/your/docx/files'
cases, complaints = process_docx_files(directory)
dataset = create_dataset(cases, complaints)

# 데이터셋을 DataFrame으로 변환
df = pd.DataFrame(dataset)

# CSV 파일로 저장
df.to_csv('legal_dataset.csv', index=False)

print(f"데이터셋이 생성되었습니다. 총 {len(dataset)}개의 케이스-소장 쌍이 있습니다.")
print("첫 번째 항목 미리보기:")
print(df.iloc[0])
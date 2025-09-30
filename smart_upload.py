from pdf2image import convert_from_path
import os
import shutil
import requests
from flask import Flask, request, jsonify
import json
import base64
import io
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

api_llm = os.getenv("API_LLM")
api_key = os.getenv("API_KEY")

app = Flask(__name__)

def convert_pdf_to_images(pdf_path,output_dir):

    try:
        images = convert_from_path(pdf_path)
        image_paths = []
        for i, image in enumerate(images):
            image_path = os.path.join(output_dir, f'page_{i+1}.jpeg')
            image.save(image_path, 'JPEG')
            image_paths.append(image_path)
        return image_paths
    
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []
    
def convert_image_to_base64(output_dir):
    image_content = []
    prompt = create_prompt()


    for image_name in os.listdir(output_dir):
        image_path = os.path.join(output_dir, image_name)
        try:
            img = Image.open(image_path)
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)
            base64_image = base64.b64encode(img_io.read()).decode('utf-8')
        except Exception as e:
            print(f"Error with image {image_path}: {e}")

        image_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })

    # ปิดท้ายด้วยข้อความ prompt
    image_content.append({
        "type": "text",
        "text": "set_response"
    })

    # สร้าง payload
    payload = {
        "model": "Qwen/Qwen2-VL-72B-Instruct-AWQ",
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            },
            {
                "role": "user",
                "content": image_content
            }
        ],
        "temperature": 0.0
    }

    # แปลงเป็น JSON string ที่ใช้ double quotes
    return payload

def api_base64(payload_all):

    url_read_text = api_llm
    headers = {
      'Content-Type': 'application/json',
      'Authorization': f"Basic {api_key}",
      'Cookie': 'Path=/'
    }

    payload = payload_all
    
    try:
        response = requests.post(url_read_text, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"API request failed with status code: {response.status_code}")
            print(f"Response text: {response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return None

def create_prompt():
    prompt = f"""คุณคือนักวิเคราะห์ข้อมูลเอกสารที่เชี่ยวชาญ
        โปรดอ่านข้อมูลด้านล่าง และดึงข้อมูลที่เกี่ยวข้องมาเก็บในรูปแบบ JSON โดยแยกตามประเภทเอกสาร (document_type) ดังนี้:

        1. ถ้า document_type คือ "bill of lading" ให้เก็บเฉพาะ: {{
        "document_type": [], 
        "as per invoice no.": [], 
        "as per proforma invoice no.": [], 
        "date": []
        }} (**ห้ามเก็บข้อมูลที่ไม่เกี่ยวข้องกับเอกสารนี้)

        2. ถ้า document_type คือ "commercial invoice" ให้เก็บเฉพาะ: {{
        "document_type": [], 
        "invoice no.": [],  **หมายเหตุ: "invoice no.", "Inv. no." และ "INV. NO." *คือข้อมูลเดียวกัน*
        "p.o. no.": [], 
        "as per proforma invoice no.": [], 
        "date": []
        }} (**ห้ามเก็บข้อมูลที่ไม่เกี่ยวข้องกับเอกสารนี้)

        3. ถ้า document_type คือ "packing list" ให้เก็บเฉพาะ: {{
        "document_type": [], 
        "invoice no.": [],  **หมายเหตุ: "invoice no.", "Inv. no." และ "INV. NO." *คือข้อมูลเดียวกัน*
        "p.o. no.": [], 
        "as per proforma invoice no.": [], 
        "date": []
        }} (**ห้ามเก็บข้อมูลที่ไม่เกี่ยวข้องกับเอกสารนี้)

        4. ถ้า document_type คือ "proforma invoice" ให้เก็บเฉพาะ: {{
        "document_type": [], 
        "invoice no.": [],  **หมายเหตุ: "invoice no.", "Inv. no." และ "INV. NO." *คือข้อมูลเดียวกัน*
        "p.o. no.": [], 
        "date": []
        }} (**ห้ามเก็บข้อมูลที่ไม่เกี่ยวข้องกับเอกสารนี้)

        5. ถ้า document_type คือ "purchase order" ให้เก็บเฉพาะ: {{
        "document_type": [], 
        "p.o. no.": [], 
        "date": []
        }} (**ห้ามเก็บข้อมูลที่ไม่เกี่ยวข้องกับเอกสารนี้)

        6. ถ้า document_type คือ "export declaration" ให้เก็บเฉพาะ: {{
        "document_type": [], 
        "invoice no.": [], **หมายเหตุ: "invoice no.", "Inv. no." และ "INV. NO." *คือข้อมูลเดียวกัน*
        "status": []
        }} (**ห้ามเก็บข้อมูลที่ไม่เกี่ยวข้องกับเอกสารนี้)

        **เงื่อนไขการจัดเก็บข้อมูล**
        - ในข้อมูลที่วิเคราะแต่ละครั้ง document_type จะมีแค่ประเภทเดียวเท่านั้น
        - ข้อมูลทุกประเภทให้จัดเก็บในรูปแบบ List เสมอ เช่น: "invoice no.": ["123456"]
        - หากไม่พบข้อมูล ให้เก็บเป็น List ว่าง
        - "invoice no.", "Inv. no." และ "INV. NO." คือข้อมูลเดียวกัน
        - กรณีเจอหลายหมายเลขในรูปแบบ: `Inv. no. : 9700010891  06/01/23,9700010892  06/01/23` ให้เก็บเฉพาะเลขที่อยู่หน้าวันที่ เช่น "invoice no.": ["9700010891", "9700010892"]
        - ให้แยกเลข invoice ออกแม้จะคั่นด้วย comma หรือช่องว่างหลายช่อง
        - หากพบหลายค่าในเอกสาร ให้เก็บทุกค่าที่พบในรูปแบบ List
        - ห้ามเก็บข้อมูลที่ไม่เกี่ยวข้องกับเอกสารนั้น ๆ
        - ข้อมูลที่เก็บในแต่ละ document_type แตกต่างกัน ต้องเก็บตาม Key ที่ระบุไว้ข้างต้นเท่านั้น*
        - "status" ให้เก็บเฉพาะข้อความก่อนวันที่ (หากมีวันที่ตามหลังไม่ต้องเก็บ)
        - ผลลัพธ์สุดท้ายต้องเป็น JSON file เท่านั้น **ห้าม**มีคำอธิบายหรือข้อความเพิ่มเติม

        **ตัวอย่างข้อมูลที่ควรระวัง**
        -  ตัวอย่างการเก็บ status ในเอกสาร เช่น STATUS=0409 จะต้องเก็บแค่ ["0409"] เท่านั้น *ห้ามเก็บข้อความ "STATUS="*
        -  ตัวอย่างการเก็บ invoice no. ในเอกสาร เช่น Inv. no. : 9700010891  06/01/23,9700010892  06/01/23 จะต้องเก็บแค่ ["9700010891", "9700010892"] เท่านั้น
        - "ใบขนสินค้า" คือ "export declaration"

        """

    return prompt


def extract_json_from_text(text):
    try:
        # Find the start and end index of the JSON string
        start_index = text.find('{')
        end_index = text.rfind('}')

        if start_index == -1 or end_index == -1 or start_index > end_index:
            print("No JSON object found in the text.")
            return None

        json_string = text[start_index : end_index + 1]

        print("Extracted JSON string:")
        print(json_string)  # <--- print string to inspect

        # Attempt to parse the JSON string
        parsed_json = json.loads(json_string)
        return parsed_json

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    
@app.route('/smart_upload', methods=['POST'])
def smart_upload():
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({
            "status": False,
            "message": "กรุณาอัปโหลดไฟล์ (Please upload a file)"
        }), 400

    file = request.files['file']
    filename = file.filename

    # เตรียมโฟลเดอร์สำหรับไฟล์และภาพ
    input_dir = "./input_files"
    output_dir = "./output_images"

    for folder in [input_dir, output_dir]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)

    # บันทึกไฟล์ต้นฉบับ
    filepath = os.path.join(input_dir, filename)
    file.save(filepath)

    # แปลงไฟล์ PDF หรือบันทึกรูปภาพ
    if filename.lower().endswith((".pdf",".PDF")):
        print("Processing PDF file")
        convert_pdf_to_images(filepath, output_dir)
    elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        print("Processing Image file")
        image = Image.open(filepath)
        image_path = os.path.join(output_dir, 'page_1.png')
        image.save(image_path, 'PNG')
    else:
        return jsonify({
            "status": False,
            "message": "รองรับเฉพาะ PDF หรือรูปภาพ JPG/PNG เท่านั้น"
        }), 400

    payload_all = convert_image_to_base64(output_dir)

    # สร้าง Prompt และเรียก LLM API
    result = api_base64(payload_all)

    # แปลงผลลัพธ์เป็น JSON (ถ้าเป็น structured response)
    extracted_json_data = extract_json_from_text(result)

    return jsonify({
        "status": True,
        "message": "Processed successfully",
        "data": {
            "filename": filename,
            "result": extracted_json_data
        }
    })

#test = smart_upload("\\data_green_sport\\BL\\BL_ 9700011472.pdf")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
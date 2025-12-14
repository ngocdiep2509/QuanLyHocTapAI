import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ Lỗi: Chưa tìm thấy GEMINI_API_KEY trong file .env")
else:
    print(f"🔑 Đang kiểm tra Key: {API_KEY[:5]}...{API_KEY[-5:]}")
    genai.configure(api_key=API_KEY)
    
    print("\n📋 Danh sách các Model mà Key này được phép dùng:")
    try:
        found = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"   - {m.name}")
                found = True
        
        if not found:
            print("⚠️ Key đúng nhưng không có model nào hỗ trợ 'generateContent'.")
    except Exception as e:
        print(f"❌ Lỗi kết nối Google: {e}")
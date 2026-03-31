import time
import argparse
from google import genai
from google.genai import types

# 10MB 대용량 영어 텍스트 (네트워크 BBR 수렴 시간을 벌기 위한 대용량 페이로드)
TEXT_10MB = "A" * 10000000  # 약 10,000,000 Byte (API 전송 한도를 고려하여 정밀 슛)

def measure_ttft(client, model_name, label, prompt):
    print(f"\n[{label}] 🚀 벤치마크 테스트를 시작합니다... (전송 크기: {len(TEXT_10MB):,} bytes)")
    start_time = time.time()
    
    try:
        response = client.models.generate_content_stream(
            model=model_name,
            contents=[prompt, TEXT_3MB],
            config=types.GenerateContentConfig(
                temperature=0.7,
            )
        )
        
        for chunk in response:
            ttft = time.time() - start_time
            print(f"[{label}] ⏱️ Time to First Token (TTFT): {ttft:.4f} 초 경과")
            print(f"[{label}] 첫 응답 토큰: {chunk.text.strip()[:20]}...")
            break # 첫 토큰만 측정하므로 스트림 루프 종료
            
    except Exception as e:
        print(f"[{label}] ❌ 에러 발생: {e}")

def main():
    parser = argparse.ArgumentParser(description="Gemini BBR vs Cubic 벤치마크 테스트 (리눅스 전용)")
    parser.add_argument("--project", required=True, help="Google Cloud 프로젝트 ID")
    parser.add_argument("--model", default="gemini-3.1-flash-lite-preview", help="테스트할 Gemini 모델")
    args = parser.parse_args()

    # 클라이언트 초기화
    # 리눅스 VM 에서 돌릴 때 글로벌 엔드포인트를 사용합니다.
    client = genai.Client(vertexai=True, project=args.project, location="global")
    
    prompt = "이 프롬프트는 3MB 대용량 데이터와 함께 전송되는 네트워크 벤치마크용 테스트 프롬프트입니다."
    
    # 슛 쏘기
    measure_ttft(client, args.model, "BBR vs Cubic 시뮬레이션", prompt)

if __name__ == "__main__":
    main()

import time
import argparse
from google import genai
from google.genai import types

# 10KB 텍스트 생성 (네트워크 데이터 전송 시간 노이즈 제거용)
TEXT_10KB = "A" * 10000  # 약 10,000 Byte (핸드셰이크 0.3초 격차가 가시적으로 시각화됨)

def measure_ttft(client, model_name, label, prompt):
    print(f"\n[{label}] 🚀 벤치마크 테스트를 시작합니다... (전송 크기: {len(TEXT_10KB):,} bytes)")
    start_time = time.time()
    
    try:
        response = client.models.generate_content_stream(
            model=model_name,
            contents=[prompt, TEXT_10KB],
            config=types.GenerateContentConfig(temperature=0.7)
        )
        
        for chunk in response:
            ttft = time.time() - start_time
            print(f"[{label}] ⏱️ Time to First Token (TTFT): {ttft:.4f} 초 경과")
            print(f"[{label}] 첫 응답 토큰: {chunk.text.strip()[:20]}...")
            break # 첫 토큰만 측정하므로 스트림 루프 종료
            
    except Exception as e:
        print(f"[{label}] ❌ 에러 발생: {e}")

def main():
    parser = argparse.ArgumentParser(description="Gemini Cold vs Warm 벤치마크 테스트 (리눅스 전용)")
    parser.add_argument("--project", required=True, help="Google Cloud 프로젝트 ID")
    parser.add_argument("--model", default="gemini-3.1-flash-lite-preview", help="테스트할 Gemini 모델")
    args = parser.parse_args()

    prompt = "이 프롬프트는 3MB 대용량 데이터와 함께 전송되는 세션 재사용용 테스트 프롬프트입니다."

    print("\n" + "="*60)
    print("🧪 [테스트 1] True Cold Start (핸드셰이크 최초 수립)")
    print("="*60)
    # Cold 슛을 쏠 때는, 연결을 최초로 맺는 깨끗한 클라이언트를 생성합니다.
    client_cold = genai.Client(vertexai=True, project=args.project, location="global")
    measure_ttft(client_cold, args.model, "Cold-Large", prompt)

    print("\n세션 안정화 및 연결 유지를 위해 10초 대기합니다...")
    time.sleep(10)

    print("\n" + "="*60)
    print("🧪 [테스트 2] True Warm Connection (동일 세션 풀 재사용)")
    print("="*60)
    # Warm 슛을 쏠 때는, 앞서 생성된 client_cold 객체를 *그대로* 재사용합니다. 
    # (내부 HTTP pool 에 커넥션이 Keep-Alive 된 채 남아있으므로 물리 전송 속도만 남음).
    measure_ttft(client_cold, args.model, "Warm-Large", prompt)

if __name__ == "__main__":
    main()

import time
import argparse
from google import genai
from google.genai import types

# 10MB 대용량 영어 텍스트 (네트워크 업로드 오버헤드 유발)
TEXT_10MB = "A" * 10000000  # 약 10,000,000 Byte (BBR 테스트와 동일한 10MB 규격)

def measure_ttft(client, model_name, label, prompt, config=None):
    print(f"\n[{label}] 🚀 벤치마크 테스트를 시작합니다... (전송 크기: {len(prompt):,} bytes)")
    start_time = time.time()
    
    try:
        response = client.models.generate_content_stream(
            model=model_name,
            contents=prompt,
            config=config
        )
        
        for chunk in response:
            ttft = time.time() - start_time
            print(f"[{label}] ⏱️ Time to First Token (TTFT): {ttft:.4f} 초 경과")
            print(f"[{label}] 첫 응답 토큰: {chunk.text.strip()[:20]}...")
            break # 첫 토큰만 측정하므로 스트림 루프 종료
            
    except Exception as e:
        print(f"[{label}] ❌ 에러 발생: {e}")

def main():
    parser = argparse.ArgumentParser(description="Gemini Context Caching 벤치마크 테스트 (리눅스 전용)")
    parser.add_argument("--project", required=True, help="Google Cloud 프로젝트 ID")
    parser.add_argument("--model", default="gemini-3.1-flash-lite-preview", help="테스트할 Gemini 모델")
    args = parser.parse_args()

    # 클라이언트 초기화
    client = genai.Client(vertexai=True, project=args.project, location="global")

    print("\n" + "="*60)
    print("🧪 [테스트 1] Context Caching 생성을 위한 사전 등록")
    print("="*60)
    
    # 10MB 더미 텍스트를 담은 캐시 생성
    try:
        cached = client.caches.create(
            model=args.model,
            config=types.CreateCachedContentConfig(
                display_name="Network_Latency_POC_10MB",
                ttl="300s",  # 5분간 유지
                contents=[TEXT_10MB]
            )
        )
        print(f"✅ 캐시 생성 완료! ID: {cached.name}")
        cache_id = cached.name
    except Exception as e:
        print(f"❌ 캐시 생성 실패: {e}")
        return

    # 10MB 대용량은 서버 측에서 인덱싱(토큰화 전처리)하는 데 시간이 걸립니다.
    print("\n✅ 서버 측 캐시 인덱싱 완전 수렴을 위해 60초간 넉넉하게 대기합니다...")
    time.sleep(60)

    print("\n" + "="*60)
    print("🧪 [테스트 2] Context Used (캐시 ID를 사용한 초극단적 응답)")
    print("="*60)
    
    # 캐시를 사용할 때는 클라이언트가 3MB를 다시 전송하지 않습니다.
    measure_ttft(
        client, 
        args.model, 
        "Context-Cached", 
        prompt="위에서 캐싱된 문서를 기반으로 짤막한 답변을 생성해줘.", 
        config=types.GenerateContentConfig(
            cached_content=cache_id
        )
    )

if __name__ == "__main__":
    main()

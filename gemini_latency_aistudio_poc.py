import time
import argparse
import os

# Google AI Studio (Gemini API) SDK 임포트
try:
    import google.generativeai as genai
except ImportError:
    print("google-generativeai 패키지가 필요합니다.")
    print("pip3 install google-generativeai 실행 후 다시 시도해주세요.")
    exit(1)

def create_large_prompt(size_in_mb):
    """
    지정된 MB 크기에 해당하는 대용량 더미 텍스트 프롬프트를 생성합니다.
    """
    print(f"[{size_in_mb}MB] 대용량 프롬프트 생성 중...")
    chunk = "A" * 1024
    return (chunk * 1024) * size_in_mb + " \n\n위 내용에 대해 아주 짧게 1문장으로 요약해줘."

def measure_ttft(model, prompt, label=""):
    """
    스트리밍 방식으로 프롬프트를 전송하고, 첫 번째 토큰이 돌아오기까지의 물리적 시간(TTFT)을 측정합니다.
    """
    print(f"[{label}] 프롬프트 전송 시작 (길이: {len(prompt):,} bytes)")
    start_time = time.time()
    
    try:
        response_stream = model.generate_content(prompt, stream=True)
        # 첫 번째 청크가 도착할 때까지 대기
        for chunk in response_stream:
            ttft = time.time() - start_time
            print(f"[{label}] ⏱️ Time to First Token (TTFT): {ttft:.4f} 초 경과")
            print(f"[{label}] 첫 응답 토큰: {chunk.text.strip()[:20]}...")
            break # 첫 토큰만 측정하므로 스트림 루프 종료
    except Exception as e:
        print(f"[{label}] ❌ 에러 발생: {e}")

def run_benchmark(api_key, model_name):
    # API Key 설정
    genai.configure(api_key=api_key)
    
    print(f"초기화 완료: 사용 모델={model_name}")
    
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"모델 로드 실패: {e}")
        return

    small_prompt = "안녕? 프랑스의 수도는 어디야?"
    large_prompt = create_large_prompt(size_in_mb=3) 
    
    print("\n" + "="*50)
    print("🧪 테스트 1: Cold Start, 대용량 프롬프트 (TCP Slow Start 포함)")
    print(" - 첫 연결이므로 DNS, TCP Handshake, TLS Handshake 비용이 포함됩니다.")
    print(" - TCP Window Size가 작게 시작되어 분할 전송(Segmentation)에 의한 RTT 왕복이 수차례 발생합니다.")
    print("="*50)
    measure_ttft(model, large_prompt, label="Cold-Large")
    
    time.sleep(1)

    print("\n" + "="*50)
    print("🧪 테스트 2: Warm Connection, 대용량 프롬프트 (오직 전송 + 추론 시간)")
    print(" - 재사용된 커넥션을 사용하므로 Handshake가 생략됩니다.")
    print(" - 이미 확장된(Scaled) TCP Window Size를 활용하여 패킷을 훨씬 큰 덩어리로 한번에 밀어넣습니다.")
    print("="*50)
    measure_ttft(model, large_prompt, label="Warm-Large")

    time.sleep(1)

    print("\n" + "="*50)
    print("🧪 테스트 3: Warm Connection, 소용량 프롬프트 (베이스라인 측정)")
    print(" - 네트워크 페이로드 전송 시간 오버헤드가 없습니다.")
    print("="*50)
    measure_ttft(model, small_prompt, label="Warm-Small")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini API (AI Studio) Network Latency PoC")
    parser.add_argument("--api_key", required=True, help="Google AI Studio API Key")
    parser.add_argument("--model", default="gemini-3.1-flash-lite-preview", help="Model Name (ex: gemini-3.1-flash-lite-preview)")
    args = parser.parse_args()
    
    run_benchmark(args.api_key, args.model)

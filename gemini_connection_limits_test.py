import asyncio
import time
import argparse
import httpx
from google import genai
from google.genai import types

# 10KB 텍스트 (단순 트래픽 오버헤드 유발)
TEXT_10KB = "A" * 10000 

async def measure_ttft_async(client, model_name, task_id):
    """
    단일 비동기 요청을 쏘고 TTFT를 측정함.
    """
    start_time = time.time()
    try:
        async def get_ttft():
            response = await client.aio.models.generate_content_stream(
                model=model_name,
                contents=["테스트 벤치마크", TEXT_10KB],
                config=types.GenerateContentConfig(temperature=0.7)
            )
            async for chunk in response:
                return time.time() - start_time
        
        ttft = await asyncio.wait_for(get_ttft(), timeout=30.0)
        print(f"[Task-{task_id}] TTFT: {ttft:.4f}초")
        return ttft
    except asyncio.TimeoutError:
        print(f"[Task-{task_id}] 타임아웃 발생 (30초 초과)")
        return None
    except Exception as e:
        print(f"[Task-{task_id}] 에러 발생: {e}")
        return None

def calculate_percentiles(times):
    """
    수집된 레이턴시 리스트에서 p50 (평균-중앙값), p95 꼬리 지연을 산출함.
    """
    if not times:
        return 0, 0
    sorted_times = sorted(times)
    n = len(sorted_times)
    
    p50_idx = int(n * 0.50)
    p95_idx = int(n * 0.95)
    
    p50 = sorted_times[min(p50_idx, n-1)]
    p95 = sorted_times[min(p95_idx, n-1)]
    
    return p50, p95

async def run_benchmark(project, model, mode, concurrency):
    print(f"\n🚀 [벤치마크 기동] 모드: {mode} | 동시 슛 개수: {concurrency}")
    
    # 모드에 따른 HTTP 클라이언트 커스텀
    if mode == "custom":
        print("🔧 [커스텀 모드] Limits (Max 1000 / Keepalive 500) 확장 적용")
        custom_limits = httpx.Limits(max_connections=1000, max_keepalive_connections=500)
        my_http_client = httpx.AsyncClient(limits=custom_limits, timeout=httpx.Timeout(60.0))
        
        # 🧪 멍키 패치: 최상위 Client는 http_client 인자를 받지 않으므로 내부 BaseApiClient의 클라이언트를 강제 교체
        client = genai.Client(vertexai=True, project=project, location="global")
        client.aio._api_client._async_httpx_client = my_http_client
    else:
        print("⚖️ [기본 모드] SDK 정적 한계값 (Max 100 / Keepalive 20) 적용")
        client = genai.Client(vertexai=True, project=project, location="global")

    tasks = []
    for i in range(concurrency):
        tasks.append(measure_ttft_async(client, model, i))

    print(f"📡 {concurrency}개의 동시 비동기 요청을 발송합니다...")
    start_all = time.time()
    results = await asyncio.gather(*tasks)
    end_all = time.time()

    valid_times = [r for r in results if r is not None]
    
    if not valid_times:
        print("❌ 유효한 측정 데이터가 존재하지 않음.")
        return

    p50, p95 = calculate_percentiles(valid_times)
    
    print("\n" + "="*50)
    print(f"📊 [결과 요약 모드: {mode}] 동시 슛: {concurrency}건")
    print("="*50)
    print(f"⏱️ 총 소요 시간 (Wall Time): {end_all - start_all:.4f} 초")
    print(f"⏱️ 성공한 요청 개수      : {len(valid_times)} / {concurrency}")
    print(f"⏱️ P50 (중앙값 TTFT)      : {p50:.4f} 초")
    print(f"⏱️ P95 (꼬리 지연 TTFT)   : {p95:.4f} 초")
    print("="*50)

def main():
    parser = argparse.ArgumentParser(description="Gemini Connection Limits 동시성 벤치마크")
    parser.add_argument("--project", required=True, help="구글 클라우드 프로젝트 ID")
    parser.add_argument("--model", default="gemini-3.1-flash-lite-preview", help="테스트할 모델")
    parser.add_argument("--mode", choices=["base", "custom"], default="base", help="기본군 vs 커스텀 확장군")
    parser.add_argument("--concurrency", type=int, default=100, help="동시 요청 개수")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.project, args.model, args.mode, args.concurrency))

if __name__ == "__main__":
    main()

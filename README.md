# 🚀 Gemini API 네트워크 지연(TTFT) 분석 및 최적화 PoC

본 프로젝트는 `google-genai` 최신 표준 SDK를 활용하여 Gemini API 전송 시 발생하는 하부 네트워크 병목(TTFT: Time to First Token)을 실측하고, 아키텍처 및 인프라 관점의 다양한 경감 기법(세션 재사용, TCP BBR, Context Caching)을 검증한 인프라스트럭처 성능 규명 PoC입니다.

---

## 📊 1. 최종 실측 데이터 (Highlights)

리눅스 VM 환경에서 **10MB (대용량 텍스트 트래픽)** 및 실측 가중치를 기반으로 도출된 최종 데이터입니다.

### 🔬 ① L7 연결 가속: Cold Start vs Warm Connection (10KB 슛 가중 평균)
| 시나리오 | TTFT 평균 (초) | 성능 격차 |
| :--- | :--- | :--- |
| **Cold Start** | 3.07s | - |
| **Warm Connection** | 2.31s | **-0.76s (약 25% 가속) 🚀** |

### 🔬 ② L4 인프라 가속: TCP BBR vs Cubic (10MB 슛 + 패킷 유실 1%)
| 혼잡 제어 알고리즘 | TTFT 실측 (초) | 성능 격차 |
| :--- | :--- | :--- |
| **Cubic (레거시 기본)** | 20.75s | - |
| **TCP BBR (가속 활성화)** | 18.41s | **-2.34s (약 11% 가속) 🚀** |

### 🔬 ③ Web API 아키텍처 가속: Context Caching (10MB 슛)
| 시나리오 | 전송 데이터 크기 | TTFT 실측 (초) |
| :--- | :--- | :--- |
| **기존 일반 업로드 대치** | 10,000,000 byte | 20.75s |
| **Context Caching 활용** | 0 byte | **10.02s (약 52% 초고속 가중!) 🚀** |

> [!TIP]
> **성능 인사이트**: Context Caching 을 통해 물리적 전송 시간(L4 병목)을 아예 `0` 으로 지워버림으로써, 순수 모델 서버 엔진의 추론 시간(Inference Latency) 단 10초만 남길 수 있습니다!

---

## 🛠️ 2. 사용 및 실행 가이드

프로젝트 저장 디렉토리에서 각각의 독립된 실행 파일들을 가동할 수 있습니다.

### 시스템 요구사항
- Python 3.10 이상
- `google-genai` 표준 SDK (`pip install google-genai`)

### 🏃‍♂️ 실행 시나리오

#### 시나리오 1: Cold / Warm 가속 프로브
```bash
python3 gemini_latency_poc.py --project <YOUR_PROJECT_ID>
```

#### 시나리오 2: TCP BBR vs Cubic 인프라 스트레스 (실행 전 `tc` 패킷 유실 주입 필요)
```bash
python3 gemini_bbr_test.py --project <YOUR_PROJECT_ID>
```

#### 시나리오 3: Context Caching (0KB 전하 가속)
```bash
python3 gemini_cache_test.py --project <YOUR_PROJECT_ID>
```

---

## 🏁 3. 최종 엔지니어링 제안 (Conclusion)

1.  **개발자 가이드**: `genai.Client()` 객체를 매 슛마다 생성하지 말고, **전역 싱글톤(Singleton)** 으로 재사용하여 HTTP 커넥션 풀을 타게 할 것 (응답 속도 25% 가속).
2.  **DevOps & 인프라 가이드**: 구글 버텍스 API 에 접하는 인터넷 게이트웨이 및 VM 노드 OS 커널에 **TCP BBR 적용** 및 Google PSC(Private Service Connect) 개설을 추진할 것.
3.  **데이터 아키텍처 가이드**: 10MB 이상의 자주 묻는 거대 덤프 기사는 네트워크 전처리 자체를 지워버리는 **컨텍스트 캐싱(Context Caching)** 을 디자인 아키텍처로 필수 도입할 것.

---


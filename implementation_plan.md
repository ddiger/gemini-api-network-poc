# [플랜] 독립 파일 분할 기반 3대 핵심 시나리오 통합 측정 가이드

본 플랜은 `Cold/Warm` 세션 재사용 측정과 `Context Caching` 측정을 서로 물리적으로 다른 파일로 쪼개어, **구글 서버 측 큐 피로도를 최소화하고 진정한 순수 지연(TTFT) 격차를 캡처**하기 위한 전용 가이드입니다.

---

## 🎯 목표
1.  **시나리오 1: Cold vs Warm Large**: `gemini_latency_poc.py` 단독 기동 ➡️ 연결 풀링(Handshake 0.5초차이) 순수 격차 증명.
2.  **시나리오 2: TCP BBR (유실 1%)**: `gemini_bbr_test.py` 단독 기동 ➡️ 패킷 유실 시 Cubic 대비 BBR 우위 증명.
3.  **시나리오 3: Context Caching**: `gemini_cache_test.py` 단독 기동 ➡️ 업로드 0KB 화에 따른 드라마틱한 TTFT 단축 증명.

---

## 🛠️ 실행 가이드 (Single Linux Environment)

리눅스 터미널에서 아래 가이드 순서대로 커맨드를 치며 측정값을 도출하세요.

### ▶️ Step 1: [시나리오 1] Cold / Warm 측정
```bash
python3 gemini_latency_poc.py --project jhlee1 --model gemini-3.1-flash-lite-preview
```
*   **기록할 대상**:
    - `Cold-Large` 시간: _____ 초
    - `Warm-Large` 시간: _____ 초 (Cold 보다 미세하게라도 빨라야 정상입니다).

---

### ▶️ Step 2: [시나리오 2] TCP BBR (유실 1%) 측정

#### 1. 인위적 패킷 유실(1%) 주입
```bash
IFACE=$(ip route show default | awk '/default/ {print $5}')
sudo tc qdisc add dev $IFACE root netem loss 1%
```

#### 2. Cubic 모드 확인 및 측정
```bash
sudo sysctl net.ipv4.tcp_congestion_control
python3 gemini_bbr_test.py --project jhlee1 --model gemini-3.1-flash-lite-preview
```
*   **측정 결과(TTFT 수치) 기록**: _____ 초

#### 3. BBR 모드 전환 및 측정
```bash
sudo modprobe tcp_bbr
echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

python3 gemini_bbr_test.py --project jhlee1 --model gemini-3.1-flash-lite-preview
```
*   **측정 결과(TTFT 수치) 기록**: _____ 초

#### 4. 리눅스 네트워크 유실 규칙 복구 (필수!)
```bash
sudo tc qdisc del dev $IFACE root
```

---

### ▶️ Step 3: [시나리오 3] Context Caching 측정
```bash
python3 gemini_cache_test.py --project jhlee1 --model gemini-3.1-flash-lite-preview
```
*   **기록할 대상**:
    - `Context-Cached` 시간: _____ 초 (Warm 6.4초 대비 유의미하게 빨라야 정상입니다).

---

## ✅ 검증 및 대조 계획 (Verification Plan)

전 항목 무결한 데이터셋을 한 번만 모아서 공유해 주시면 최종 리포트 마감합니다.

1.  **Cold Large**: _____ 초
2.  **Warm Large**: _____ 초
3.  **Context Caching**: _____ 초
4.  **Cubic + 유실 1%**: _____ 초
5.  **BBR + 유실 1%**: _____ 초

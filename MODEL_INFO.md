# LLM 모델 정보

## 사용 중인 모델

### API 모드 (기본값, 권장)
- **LLM**: OpenAI GPT-4o-mini
- **Embedding**: text-embedding-3-small (1536차원)
- **특징**: 빠르고 정확, API 키 필요

### LOCAL 모드 (Ollama)
- **LLM**: Qwen2.5-Coder-3B
- **Embedding**: nomic-embed-text (768차원)
- **특징**: 로컬 실행, API 키 불필요, GPU 권장

---

## Qwen2.5-Coder-3B 특징

### 장점
✅ **코딩 특화**: 코드 생성 및 이해에 최적화
✅ **작은 크기**: 3B 파라미터로 8GB RAM에서도 실행 가능
✅ **빠른 추론**: llama3.2:3b 대비 코딩 작업에서 더 우수한 성능
✅ **다국어 지원**: 한국어, 영어, 중국어 등 지원
✅ **무료**: 로컬에서 무제한 사용 가능

### 단점
⚠️ **GPU 권장**: CPU만으로는 느릴 수 있음
⚠️ **메모리**: 최소 4-6GB RAM 필요
⚠️ **일반 대화**: GPT-4에 비해 일반 대화 품질은 낮을 수 있음

---

## 모델 변경 방법

### 1. 로컬에서 테스트

```bash
# Qwen2.5-Coder-3B 다운로드
ollama pull qwen2.5-coder:3b

# 테스트
ollama run qwen2.5-coder:3b "Hello, tell me about GraphRAG"

# .env에서 LOCAL 모드 설정
RUN_MODE=LOCAL

# 서버 재시작
python src/app.py
```

### 2. Docker에서 사용

```bash
# .env 파일 수정
RUN_MODE=LOCAL

# 배포 (모델 자동 다운로드)
./deploy.sh
```

Docker 배포 시 `ollama-loader` 컨테이너가 자동으로 모델을 다운로드합니다.

---

## 다른 모델로 변경하기

### Ollama 지원 모델

**코딩 특화:**
- `qwen2.5-coder:3b` (현재 사용 중)
- `qwen2.5-coder:7b` (더 강력, 더 많은 메모리 필요)
- `codellama:7b`

**일반 대화:**
- `llama3.2:3b` (이전 기본 모델)
- `llama3.1:8b` (더 강력)
- `mistral:7b`

### 변경 방법

1. **`src/config.py` 수정:**

```python
LOCAL_MODELS = {
    "llm": "qwen2.5-coder:7b",  # 원하는 모델로 변경
    "embedding": "nomic-embed-text",
    "embedding_dim": 768,
}
```

2. **`docker-compose.yml` 수정 (Docker 사용 시):**

```yaml
ollama-loader:
  entrypoint: |
    sh -c "
      echo 'Downloading qwen2.5-coder:7b model...'
      curl -X POST http://ollama:11434/api/pull -d '{\"name\":\"qwen2.5-coder:7b\"}'
      ...
    "
```

3. **재배포:**

```bash
./deploy.sh
```

---

## 성능 비교 (참고)

| 모델 | 크기 | 메모리 | 속도 | 코딩 | 일반대화 |
|------|------|--------|------|------|----------|
| GPT-4o-mini | API | N/A | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Qwen2.5-Coder:3B | 3B | 4-6GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Qwen2.5-Coder:7B | 7B | 8-12GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Llama3.2:3B | 3B | 4-6GB | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 추천 설정

### 프로덕션 (팀원 공유)
- **모드**: API (GPT-4o-mini)
- **이유**: 안정성, 속도, 품질이 가장 우수

### 개발/테스트 (로컬)
- **모드**: LOCAL (Qwen2.5-Coder-3B)
- **이유**: API 비용 절감, 빠른 반복 개발

### GPU 서버 (클라우드)
- **모드**: LOCAL (Qwen2.5-Coder:7B)
- **이유**: 강력한 성능 + 무료 사용

---

## 문제 해결

### Ollama 모델 다운로드 실패

```bash
# Docker 컨테이너 로그 확인
docker-compose logs ollama-loader

# 수동으로 다운로드
docker-compose exec ollama ollama pull qwen2.5-coder:3b
```

### 메모리 부족

```bash
# 더 작은 모델 사용
# config.py에서
"llm": "qwen2.5-coder:1.5b"  # 또는 다른 작은 모델
```

### GPU 미사용

```bash
# GPU 상태 확인
nvidia-smi

# Docker GPU 지원 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

---

**참고 링크:**
- Qwen2.5-Coder: https://ollama.com/library/qwen2.5-coder
- Ollama Models: https://ollama.com/library
- Ollama Docs: https://github.com/ollama/ollama

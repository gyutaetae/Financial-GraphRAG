
cd /Users/gyuteoi/Desktop/graphrag/Finance_GraphRAG
source .venv/bin/activate

# logs 디렉토리 생성
mkdir -p logs

# 기존 FastAPI 서버 프로세스 종료
echo "기존 FastAPI 서버 종료 중..."
pkill -f "python.*app.py" || true
pkill -f "uvicorn.*app:app" || true
sleep 2

# FastAPI 서버 백그라운드 실행
echo "FastAPI 서버 시작 중..."
nohup python src/app.py > logs/fastapi.log 2>&1 &
FASTAPI_PID=$!
echo "FastAPI 서버 시작됨 (PID: $FASTAPI_PID)"
echo "로그 확인: tail -f logs/fastapi.log"

# 서버가 시작될 때까지 대기
echo "서버 준비 대기 중..."
sleep 5

# 서버 상태 확인
if curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "FastAPI 서버 정상 작동 중!"
else
    echo "FastAPI 서버 응답 없음. 로그를 확인해주세요: tail -f logs/fastapi.log"
fi

# Streamlit UI 실행 (포그라운드)
echo "Streamlit UI 시작 중..."
streamlit run src/streamlit_app.py --server.port 8501

# Streamlit 종료 시 FastAPI 서버도 종료
echo "FastAPI 서버 종료 중..."
kill $FASTAPI_PID 2>/dev/null || true

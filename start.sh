#!/bin/bash

# Finance GraphRAG 로컬 실행 스크립트

cd "$(dirname "$0")"

echo "🚀 Finance GraphRAG 시작 중..."

# 1. FastAPI 백엔드 시작 (백그라운드)
echo "📡 FastAPI 백엔드 시작..."
python3 src/app.py > /tmp/finance_graphrag_backend.log 2>&1 &
BACKEND_PID=$!

# 백엔드 시작 대기
sleep 3

# 백엔드 상태 확인
if ps -p $BACKEND_PID > /dev/null; then
   echo "✅ 백엔드 실행 중 (PID: $BACKEND_PID)"
else
   echo "❌ 백엔드 시작 실패. 로그 확인: tail -f /tmp/finance_graphrag_backend.log"
   exit 1
fi

# 2. Streamlit 프론트엔드 실행
echo "🖥️ Streamlit 대시보드 시작..."
echo "📍 브라우저에서 http://localhost:8501 접속하세요"
streamlit run src/streamlit_app.py

# Streamlit 종료 시 백엔드도 종료
echo "🛑 서비스 종료 중..."
kill $BACKEND_PID 2>/dev/null
echo "✅ 종료 완료"

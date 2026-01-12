#!/bin/bash

echo "🚀 Finance GraphRAG 팀 협업 모드 시작..."
echo ""

# 환경 변수 파일 확인
if [ ! -f .env.docker ]; then
    echo "❌ .env.docker 파일이 없습니다!"
    echo "📝 .env.docker 파일을 생성하고 API 키를 설정하세요."
    exit 1
fi

# 기존 컨테이너 정리
echo "🧹 기존 컨테이너 정리 중..."
docker-compose down

# 모든 서비스 시작
echo "🐳 Docker 컨테이너 시작 중..."
docker-compose --env-file .env.docker up -d

echo ""
echo "✅ 시작 완료!"
echo ""
echo "📊 접속 정보:"
echo "  - Streamlit UI: http://localhost:8501"
echo "  - FastAPI 백엔드: http://localhost:8000"
echo "  - Neo4j 브라우저: http://localhost:7474"
echo ""
echo "👥 팀원들에게 공유할 주소:"
echo "  - 로컬 네트워크에서: http://$(ipconfig getifaddr en0):8501"
echo "  - 또는 내 IP 주소 확인: ifconfig | grep 'inet '"
echo ""
echo "📝 로그 확인: docker-compose logs -f"
echo "🛑 종료: docker-compose down"

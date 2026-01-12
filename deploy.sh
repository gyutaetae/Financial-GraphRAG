#!/bin/bash

# Finance GraphRAG Docker 배포 스크립트
# 사용법: ./deploy.sh

set -e

echo "================================================"
echo "  Finance GraphRAG Docker 배포 스크립트"
echo "  LLM 모델: Qwen2.5-Coder-3B (Ollama)"
echo "================================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Docker 설치 확인
echo "🔍 Docker 설치 확인 중..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker가 설치되어 있지 않습니다.${NC}"
    echo "Docker Desktop을 설치해주세요: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose가 설치되어 있지 않습니다.${NC}"
    echo "Docker Compose를 설치해주세요."
    exit 1
fi

echo -e "${GREEN}✅ Docker 설치 확인 완료${NC}"
echo ""

# 2. .env 파일 확인
echo "🔍 환경 변수 파일(.env) 확인 중..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다.${NC}"
    echo "env.docker.example을 .env로 복사합니다..."
    cp env.docker.example .env
    echo ""
    echo -e "${YELLOW}⚠️  .env 파일을 편집해서 API 키를 입력해주세요:${NC}"
    echo "  - OPENAI_API_KEY (필수)"
    echo "  - NEO4J_PASSWORD (필수)"
    echo "  - TAVILY_API_KEY (선택)"
    echo ""
    read -p "계속하려면 Enter를 누르세요 (편집 후)..."
fi

# API 키 확인
if ! grep -q "sk-proj" .env && ! grep -q "sk-[A-Za-z0-9]" .env; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY가 설정되지 않은 것 같습니다.${NC}"
    read -p "계속하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ 환경 변수 확인 완료${NC}"
echo ""

# 3. 기존 컨테이너 정리 (선택)
echo "🧹 기존 컨테이너 정리..."
read -p "기존 컨테이너를 중지하고 삭제하시겠습니까? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down
    echo -e "${GREEN}✅ 기존 컨테이너 정리 완료${NC}"
else
    echo "기존 컨테이너 유지"
fi
echo ""

# 4. Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker-compose build --no-cache
echo -e "${GREEN}✅ 이미지 빌드 완료${NC}"
echo ""

# 5. 컨테이너 실행
echo "🚀 컨테이너 실행 중..."
docker-compose up -d
echo -e "${GREEN}✅ 컨테이너 실행 완료${NC}"
echo ""

# 6. 상태 확인
echo "📊 컨테이너 상태 확인 중..."
sleep 5
docker-compose ps
echo ""

# 7. Health Check
echo "🏥 서비스 헬스 체크 중..."
sleep 10

# Backend Health Check
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend (FastAPI): 정상 작동${NC}"
else
    echo -e "${RED}❌ Backend (FastAPI): 응답 없음${NC}"
    echo "로그를 확인하세요: docker-compose logs backend"
fi

# Frontend Check
if curl -s http://localhost:8501 > /dev/null; then
    echo -e "${GREEN}✅ Frontend (Streamlit): 정상 작동${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend (Streamlit): 아직 시작 중일 수 있습니다${NC}"
fi

# Neo4j Check
if curl -s http://localhost:7474 > /dev/null; then
    echo -e "${GREEN}✅ Neo4j: 정상 작동${NC}"
else
    echo -e "${RED}❌ Neo4j: 응답 없음${NC}"
    echo "로그를 확인하세요: docker-compose logs neo4j"
fi

echo ""
echo "================================================"
echo "  🎉 배포 완료!"
echo "================================================"
echo ""
echo "접속 URL:"
echo "  - Streamlit UI:    http://localhost:8501"
echo "  - FastAPI Docs:    http://localhost:8000/docs"
echo "  - Neo4j Browser:   http://localhost:7474"
echo ""
echo "로그 확인:"
echo "  docker-compose logs -f"
echo ""
echo "컨테이너 중지:"
echo "  docker-compose down"
echo ""
echo "도메인 스키마 초기화:"
echo "  curl -X POST http://localhost:8000/domain/schema/init"
echo ""

# 8. 로컬 네트워크 IP 표시
echo "팀원 공유 URL:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LOCAL_IP=$(hostname -I | awk '{print $1}')
else
    LOCAL_IP="YOUR_IP"
fi

if [ ! -z "$LOCAL_IP" ]; then
    echo "  - Streamlit UI:    http://${LOCAL_IP}:8501"
    echo "  - FastAPI Docs:    http://${LOCAL_IP}:8000/docs"
else
    echo "  - IP 주소를 확인한 후 공유하세요"
fi
echo ""

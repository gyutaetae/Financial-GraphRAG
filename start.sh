#!/bin/bash

# 1. OrbStack으로 Neo4j 엔진 켜기
echo "🚀 Neo4j 엔진 가동 중..."
docker-compose up -d

# 2. 잠시 기다리기 (엔진이 완전히 켜질 시간)
sleep 5

# 3. 스트림릿 웹사이트 실행하기
echo "🖥️ 스트림릿 대시보드 접속 중..."
streamlit run app.py
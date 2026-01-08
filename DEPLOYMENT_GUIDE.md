# 배포 가이드 - 웹에서 접속 가능하게 만들기

## 🚀 방법 1: Streamlit Cloud (가장 간단, 무료)

### 장점
- ✅ 완전 무료
- ✅ 자동 HTTPS 지원
- ✅ 자동 배포 (GitHub 푸시 시 자동 업데이트)
- ✅ 설정 간단

### 단계

1. **GitHub 저장소 준비**
   ```bash
   # 이미 완료되어 있음
   # https://github.com/gyutaetae/Financial-GraphRAG
   ```

2. **Streamlit Cloud 접속**
   - https://share.streamlit.io/ 접속
   - GitHub 계정으로 로그인

3. **앱 배포**
   - "New app" 클릭
   - Repository: `gyutaetae/Financial-GraphRAG` 선택
   - Branch: `main` 선택
   - Main file path: `src/streamlit_app.py` 입력
   - "Deploy!" 클릭

4. **Secrets 설정** (Settings → Secrets)
   ```toml
   OPENAI_API_KEY = "sk-your-actual-api-key-here"
   OPENAI_BASE_URL = "https://api.openai.com/v1"
   ```

5. **완료!**
   - 앱 URL: `https://your-app-name.streamlit.app`
   - 누구나 접속 가능!

---

## 🌐 방법 2: 클라우드 서버 (AWS, GCP, Azure 등)

### AWS EC2 배포 예시

#### 1. EC2 인스턴스 생성

```bash
# Ubuntu 22.04 LTS 인스턴스 생성
# 인스턴스 타입: t3.medium 이상 권장
# 보안 그룹 설정:
#   - 포트 8501 (Streamlit) 열기
#   - 포트 8000 (FastAPI) 열기 (선택)
#   - 포트 7474 (Neo4j Browser) 열기 (선택)
```

#### 2. 서버 접속 및 설정

```bash
# SSH 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 프로젝트 클론
git clone https://github.com/gyutaetae/Financial-GraphRAG.git
cd Financial-GraphRAG

# .env 파일 설정
cp .env.example .env
nano .env  # API 키 및 비밀번호 설정
```

#### 3. Docker Compose 실행

```bash
# 백그라운드로 실행
docker-compose up -d

# 서비스 확인
docker-compose ps
```

#### 4. 방화벽 설정 (AWS Security Group)

- 인바운드 규칙 추가:
  - 포트 8501: 0.0.0.0/0 (Streamlit)
  - 포트 8000: 0.0.0.0/0 (FastAPI, 선택)
  - 포트 7474: 0.0.0.0/0 (Neo4j, 선택)

#### 5. 접속

- Streamlit: `http://your-ec2-public-ip:8501`
- FastAPI: `http://your-ec2-public-ip:8000`

---

## 🔒 방법 3: 도메인 연결 + HTTPS (프로덕션)

### Nginx 리버스 프록시 설정

#### 1. Nginx 설치

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

#### 2. Nginx 설정 파일 생성

```bash
sudo nano /etc/nginx/sites-available/finance-graphrag
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

#### 3. 설정 활성화

```bash
sudo ln -s /etc/nginx/sites-available/finance-graphrag /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 4. SSL 인증서 발급 (Let's Encrypt)

```bash
sudo certbot --nginx -d your-domain.com
```

#### 5. 완료!

- HTTPS URL: `https://your-domain.com`
- 자동 HTTPS 리다이렉트
- 보안 인증서 자동 갱신

---

## 🐳 방법 4: Docker + 클라우드 서버 (권장)

### 전체 스택 배포

#### docker-compose.yml 수정 (프로덕션용)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    # ... 기존 설정 ...
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    # 포트를 내부 네트워크로만 제한
    # ports:
    #   - "8000:8000"  # 주석 처리 (Nginx를 통해서만 접근)

  frontend:
    # ... 기존 설정 ...
    environment:
      - API_BASE_URL=http://backend:8000
    # 포트를 내부 네트워크로만 제한
    # ports:
    #   - "8501:8501"  # 주석 처리 (Nginx를 통해서만 접근)
```

### 배포 스크립트

```bash
#!/bin/bash
# deploy.sh

# 환경 변수 확인
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

# Docker 이미지 빌드
docker-compose -f docker-compose.prod.yml build

# 기존 컨테이너 중지
docker-compose -f docker-compose.prod.yml down

# 새 컨테이너 시작
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 📊 배포 방법 비교

| 방법 | 난이도 | 비용 | HTTPS | 자동 배포 | 추천 |
|------|--------|------|-------|-----------|------|
| Streamlit Cloud | ⭐ 쉬움 | 무료 | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| AWS EC2 | ⭐⭐ 보통 | $10-50/월 | ❌ | ❌ | ⭐⭐⭐ |
| AWS EC2 + Nginx | ⭐⭐⭐ 어려움 | $10-50/월 | ✅ | ❌ | ⭐⭐⭐⭐ |
| Docker + 클라우드 | ⭐⭐⭐ 어려움 | $20-100/월 | ✅ | ✅ | ⭐⭐⭐⭐⭐ |

---

## 🔐 보안 체크리스트

배포 전 확인:

- [ ] `.env` 파일이 Git에 커밋되지 않음
- [ ] 강력한 Neo4j 비밀번호 설정
- [ ] OpenAI API 키가 안전하게 관리됨
- [ ] 방화벽 설정 (필요한 포트만 열기)
- [ ] HTTPS 사용 (프로덕션)
- [ ] 정기적인 백업 설정

---

## 🚨 문제 해결

### 외부에서 접속 불가

1. **방화벽 확인**
   ```bash
   # AWS Security Group 확인
   # 로컬 방화벽 확인
   sudo ufw status
   ```

2. **포트 확인**
   ```bash
   # 서버에서 포트 리스닝 확인
   sudo netstat -tlnp | grep 8501
   ```

3. **Docker 포트 바인딩 확인**
   ```bash
   docker-compose ps
   docker port finance-graphrag-frontend
   ```

### SSL 인증서 오류

```bash
# 인증서 갱신
sudo certbot renew

# Nginx 재시작
sudo systemctl restart nginx
```

---

## 📚 추가 자료

- [Streamlit Cloud 문서](https://docs.streamlit.io/streamlit-community-cloud)
- [AWS EC2 가이드](https://aws.amazon.com/ec2/)
- [Nginx 설정 가이드](https://nginx.org/en/docs/)
- [Let's Encrypt 문서](https://letsencrypt.org/docs/)

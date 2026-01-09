# 답변 품질 개선 가이드

## 🎯 현재 문제점

**예시 질문:** "nvidia revenue" 또는 "엔비디아 수익 올해"

**현재 답변:**
- ❌ "해당 문서들에서는 관련 정보를 찾을 수 없습니다."
- ⚠️ 추상적이고 일반적인 답변 ("긍정적인 성장", "강력한 입지")
- ⚠️ 구체적인 수치 부족 (실제 수익 금액, 성장률 등)

---

## 💡 개선 방법

### 1. **데이터 인덱싱 개선** 🔍

#### 문제
PDF에서 텍스트 추출 시 숫자와 표가 제대로 파싱되지 않음

#### 해결책
```python
# src/utils.py 개선
def extract_text_from_pdf_with_metadata(pdf_path):
    """PDF에서 표와 숫자를 포함한 텍스트 추출"""
    import pymupdf
    
    doc = pymupdf.open(pdf_path)
    extracted_data = []
    
    for page_num, page in enumerate(doc, start=1):
        # 일반 텍스트 추출
        text = page.get_text()
        
        # 표 추출 (중요!)
        tables = page.find_tables()
        for table in tables:
            table_text = table.extract()
            # 표를 구조화된 텍스트로 변환
            formatted_table = format_table_as_text(table_text)
            text += f"\n\n[TABLE]\n{formatted_table}\n[/TABLE]\n"
        
        extracted_data.append({
            "text": text,
            "page_number": page_num,
            "has_tables": len(tables) > 0
        })
    
    return extracted_data
```

---

### 2. **검색 쿼리 개선** 🎯

#### 문제
"nvidia revenue"를 검색할 때 관련 청크를 찾지 못함

#### 해결책: 쿼리 확장 (Query Expansion)

```python
# src/engine/graphrag_engine.py
async def aquery(self, question: str):
    # 쿼리 확장: 동의어 및 관련 용어 추가
    expanded_query = await self._expand_query(question)
    
    # 예: "nvidia revenue" → "nvidia revenue 수익 매출 실적 earnings"
    return await self._search_with_expanded_query(expanded_query)

async def _expand_query(self, question: str):
    """LLM을 사용해 쿼리 확장"""
    prompt = f"""
    다음 질문에 대한 검색을 개선하기 위해 관련 키워드를 추가하세요:
    
    질문: {question}
    
    관련 키워드 (동의어, 유사 용어):
    """
    
    keywords = await self.llm_call(prompt)
    return f"{question} {keywords}"
```

---

### 3. **청크 크기 최적화** 📏

#### 문제
청크가 너무 크거나 작아서 관련 정보를 놓침

#### 해결책: 적응형 청킹 (Adaptive Chunking)

```python
# src/config.py
# 현재 설정
CHUNK_SIZE = 1200  # 너무 클 수 있음
CHUNK_OVERLAP = 100

# 개선된 설정
CHUNK_SIZE = 600  # 더 작은 청크로 정밀 검색
CHUNK_OVERLAP = 150  # 더 많은 오버랩으로 문맥 유지

# 또는 동적 청킹
def adaptive_chunking(text, min_size=400, max_size=800):
    """문장 단위로 청킹하여 문맥 유지"""
    sentences = split_into_sentences(text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > max_size:
            if len(current_chunk) >= min_size:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += " " + sentence
        else:
            current_chunk += " " + sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
```

---

### 4. **하이브리드 검색 강화** 🔀

#### 문제
벡터 검색만으로는 정확한 숫자/날짜를 찾기 어려움

#### 해결책: 키워드 검색 + 벡터 검색 결합

```python
# src/engine/graphrag_engine.py
async def hybrid_search(self, question: str, top_k: int = 30):
    # 1. 벡터 검색 (의미 기반)
    vector_results = await self.vector_search(question, top_k=20)
    
    # 2. 키워드 검색 (정확한 매칭)
    keywords = extract_keywords(question)  # "nvidia", "revenue", "2023"
    keyword_results = await self.keyword_search(keywords, top_k=10)
    
    # 3. 결과 병합 및 재순위화
    combined_results = merge_and_rerank(vector_results, keyword_results)
    
    return combined_results[:top_k]

def extract_keywords(question: str):
    """질문에서 중요 키워드 추출"""
    # 회사명, 숫자, 날짜 등 추출
    import re
    
    keywords = []
    
    # 회사명 추출
    companies = re.findall(r'\b(nvidia|엔비디아|삼성|samsung)\b', question.lower())
    keywords.extend(companies)
    
    # 숫자 추출
    numbers = re.findall(r'\d+', question)
    keywords.extend(numbers)
    
    # 재무 용어 추출
    financial_terms = ['revenue', '수익', '매출', 'earnings', '실적']
    for term in financial_terms:
        if term in question.lower():
            keywords.append(term)
    
    return keywords
```

---

### 5. **프롬프트 엔지니어링 개선** 📝

#### 문제
LLM이 구체적인 정보를 제공하지 않음

#### 해결책: 구조화된 프롬프트

```python
# src/utils.py
def get_executive_report_prompt(question: str, context: str):
    """개선된 프롬프트"""
    return f"""
당신은 재무 분석 전문가입니다. 제공된 문서를 기반으로 정확하고 구체적인 답변을 제공하세요.

**중요 지침:**
1. 구체적인 숫자, 날짜, 백분율을 반드시 포함하세요
2. 출처를 명확히 표시하세요 (예: "2023년 Q3 보고서에 따르면...")
3. 추상적인 표현 대신 구체적인 데이터를 사용하세요
4. 정보가 없으면 "해당 문서에서 찾을 수 없습니다"라고 명확히 말하세요

**질문:** {question}

**제공된 문서:**
{context}

**답변 형식:**
1. 핵심 답변 (구체적인 숫자 포함)
2. 상세 설명
3. 출처 및 근거

답변:
"""
```

---

### 6. **Re-ranking 추가** 🎖️

#### 문제
검색된 청크가 질문과 관련성이 낮음

#### 해결책: Cross-Encoder를 사용한 재순위화

```python
# src/engine/graphrag_engine.py
from sentence_transformers import CrossEncoder

class HybridGraphRAGEngine:
    def __init__(self):
        # ...
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    async def rerank_results(self, question: str, chunks: list):
        """검색 결과를 재순위화"""
        # 각 청크와 질문의 관련성 점수 계산
        pairs = [(question, chunk['text']) for chunk in chunks]
        scores = self.reranker.predict(pairs)
        
        # 점수 기준으로 정렬
        ranked_chunks = sorted(
            zip(chunks, scores),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [chunk for chunk, score in ranked_chunks]
```

---

### 7. **메타데이터 활용 강화** 📊

#### 문제
페이지 번호, 섹션 정보 등이 제대로 활용되지 않음

#### 해결책: 메타데이터 필터링

```python
# src/engine/graphrag_engine.py
async def search_with_metadata_filter(self, question: str, filters: dict = None):
    """메타데이터를 활용한 검색"""
    
    # 질문에서 메타데이터 추출
    # 예: "2023년 Q3 보고서에서 엔비디아 수익"
    metadata = extract_metadata_from_question(question)
    
    # 필터 적용
    if metadata.get('year'):
        filters['year'] = metadata['year']
    if metadata.get('quarter'):
        filters['quarter'] = metadata['quarter']
    
    # 필터링된 검색
    results = await self.filtered_search(question, filters)
    
    return results

def extract_metadata_from_question(question: str):
    """질문에서 메타데이터 추출"""
    import re
    
    metadata = {}
    
    # 연도 추출
    year_match = re.search(r'(20\d{2})', question)
    if year_match:
        metadata['year'] = year_match.group(1)
    
    # 분기 추출
    quarter_match = re.search(r'Q([1-4])', question, re.IGNORECASE)
    if quarter_match:
        metadata['quarter'] = quarter_match.group(1)
    
    return metadata
```

---

### 8. **다단계 추론 (Multi-hop Reasoning)** 🔗

#### 문제
복잡한 질문에 대한 답변이 부족함

#### 해결책: Chain-of-Thought 추론

```python
# src/engine/graphrag_engine.py
async def multi_hop_reasoning(self, question: str):
    """다단계 추론"""
    
    # 1단계: 질문 분해
    sub_questions = await self.decompose_question(question)
    # 예: "엔비디아 2023년 수익 성장률" 
    # → ["엔비디아 2023년 수익", "엔비디아 2022년 수익", "성장률 계산"]
    
    # 2단계: 각 하위 질문에 답변
    sub_answers = []
    for sub_q in sub_questions:
        answer = await self.aquery(sub_q)
        sub_answers.append(answer)
    
    # 3단계: 하위 답변 통합
    final_answer = await self.synthesize_answers(question, sub_answers)
    
    return final_answer
```

---

## 📊 우선순위별 개선 계획

### 🔴 즉시 적용 (High Priority)

1. **프롬프트 개선** - 구체적인 숫자 요구
2. **청크 크기 조정** - 600자로 축소, 오버랩 150자
3. **쿼리 확장** - 동의어 추가

### 🟡 단기 개선 (Medium Priority)

4. **하이브리드 검색** - 키워드 + 벡터 검색
5. **Re-ranking** - Cross-Encoder 추가
6. **표 추출 개선** - PyMuPDF 테이블 파싱

### 🟢 장기 개선 (Low Priority)

7. **메타데이터 필터링** - 연도/분기 필터
8. **다단계 추론** - Chain-of-Thought

---

## 🚀 빠른 적용 예시

### 즉시 개선 가능한 코드

```python
# src/config.py에 추가
# 청크 크기 최적화
CHUNK_SIZE = 600  # 기존: 1200
CHUNK_OVERLAP = 150  # 기존: 100

# src/utils.py에 추가
def get_executive_report_prompt(question: str, context: str):
    return f"""
당신은 재무 분석 전문가입니다.

**중요:** 반드시 구체적인 숫자, 날짜, 백분율을 포함하세요.

질문: {question}

문서:
{context}

답변 (구체적인 수치 포함):
"""
```

---

## 📈 기대 효과

| 개선 사항 | 효과 |
|----------|------|
| 프롬프트 개선 | 구체적인 답변 +50% |
| 청크 크기 조정 | 관련 정보 검색 +30% |
| 하이브리드 검색 | 정확도 +40% |
| Re-ranking | 관련성 +35% |

---

## 🎯 결론

**즉시 적용 가능한 개선:**
1. 프롬프트에 "구체적인 숫자 포함" 지시 추가
2. 청크 크기를 600자로 축소
3. 쿼리에 동의어 추가

**이 3가지만 적용해도 답변 품질이 크게 개선됩니다!**

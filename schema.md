나중에 여기에 neo4j schema를 텍스트나 이미지로 저장한다음에

"Check @schema.md and @cursorrules to write a specialized Cypher query that finds the correlation between 'Quarterly Revenue' and 'Internal Risk Factors'."

이렇게 하면 커서가 네 DB 구조를 완벽히 파악하고 소름 돋을 정도로 정확한 쿼리를 짜줄 겁니다.

Local vs. API Benchmarking: Ollama와 API의 결과물 차이를 자동으로 비교해 주는 Eval Pipeline을 먼저 짜보는 건 어떨까요? "깊이"의 차이를 측정할 수 있어야 개선도 가능합니다.

Graph Visualization: Streamlit에서 복잡한 그래프를 어떻게 시각화할 건가요? streamlit-agraph나 pyvis 같은 라이브러리를 쓸 때 발생할 Performance Bottleneck에 대한 규칙도 필요할 겁니다.


커서 설정에서 모델을 o1-mini로 바꾸고, 네 프로젝트의 가장 난해한 파일 하나를 골라 이렇게 물어보세요:

"이 로직에서 성능 병목이 생길 수 있는 지점 3곳을 찾고, 토큰 효율을 극대화할 수 있는 리팩토링 안을 제안해줘."

이렇게 '분석'은 o1-mini에게 시키고, 실제 '코드 작성'은 Claude 4.5에게 시키는 모델 분업

plan
언제 쓰나: 작업이 너무 커서 어디서부터 손대야 할지 모를 때 씁니다. Plan 모드에서 확정된 계획을 에이전트에게 넘겨주는 것이 2026년의 Best Practice입니다.


Plan 모드에서 Claude 4.5 Sonnet으로 전체 설계를 잡습니다.

설계가 맘에 들면 Agent 모드로 전환하고 모델을 GPT-5 Standard로 바꿔서 실행(Build) 시킵니다.

중간에 에러가 나면 Debug 모드로 범인을 잡습니다.

반복적인 스타일 수정이나 단순 작업은 Composer
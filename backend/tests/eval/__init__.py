"""DeepEval LLM evaluation harness — Sprint 4 (L4 dim 7).

Tests dans ce package :
- DEPENDENT d'un LLM judge externe (OpenAI ou DeepSeek/local)
- POTENTIELLEMENT PAYANT (DeepEval default judge = gpt-4o-mini)
- Skipped si OPENAI_API_KEY absent ET LOCAL_LLM_JUDGE_URL absent

Run :
    pytest backend/tests/eval/ --no-cov           # judge réel (payant)
    pytest backend/tests/eval/ --deepeval-skip-eval  # struct only, gratuit
"""

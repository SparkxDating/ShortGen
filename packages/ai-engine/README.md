# ai-engine

Adapter package for future multi-provider LLM routing.

Phase 1 leaves `app/services/llm.py` untouched. The SaaS worker reaches
script generation through `packages/video-engine/video_engine/generation_adapter.py`.

"""Finite controller-owned synthetic recipe. Not a model/tool issuance endpoint."""
from pathlib import Path
PHASE=Path('D:/Hermes/knowledge/hallym/intake/parallel/make-collaboration/cross-bot-cost-2756D15D/runtime-integration3-608159D2')
ROOTS={name:PHASE/('worker' if name in ('DEVELOPMENT','WRITER') else 'independent-check')/'scratch'/name for name in ('DEVELOPMENT','WRITER','PARENT','REVIEW')}
USER='Return SYNTHETIC_OK only.'
SYSTEM='Synthetic public source packet. No tools. No private data.'
KEY='SYNTHETIC-ONLY-2108ae-NOT-A-REAL-KEY'
MODEL='gemini-3.8-flash'
URL='https://generativelanguage.googleapis.com/v1beta/models/'+MODEL+':generateContent'
CASES=('success','continuation','thinking','timeout','429','500','empty','tool','concurrent','processrace','callback','fallback','title','compression','refresh','expiry')
PREFIX='SYNTHETIC_ONLY_608159D2_'
VALID_FROM='2026-11-01'
VALID_THROUGH='2026-12-31'
NAMESPACE_MAX_KRW=1000
LIVE_ENTRY_ENABLED=False

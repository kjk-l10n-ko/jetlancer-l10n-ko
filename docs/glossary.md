# Glossary — Jet Lancer Korean Patch

| English | 한국어 | Notes |
|---------|--------|-------|
| Jet Lancer | 제트 랜서 |
| Ash | 애쉬 |
| Aegis | 이지스 |
| Rival | 라이벌 |
| Captain | 캡틴 |
| Sky Pirates | 하늘 해적 |
| Gin | 진 |
| Engineer | 엔지니어 |
| Hacker | 해커 |
| Shields | 쉴드 |
| Hull | 선체 |
| Missile | 미사일 |
| Cannon | 캐논 |
| Laser | 레이저 |
| Flare | 플레어 |
| Boost | 부스트 |
| Afterburner | 애프터버너 |
| Target | 표적 |
| Lock-on | 락온 |
| Enemy | 적 |
| Ally | 아군 |
| Squadron | 편대 |
| Formation | 대형 |
| Comms | 통신 |
| Hangar | 격납고 |
| Mission | 임무 |
| Contract | 계약 |
| Credits | 크레딧 |
| Difficulty | 난이도 |
| Controls | 조작 |
| Options | 설정 |
| Main Menu | 메인 메뉴 |
| Pause | 일시정지 |
| Quit | 종료 |
| Retry | 재시도 |
| Continue | 계속 |
| Save | 저장 |
| Load | 불러오기 |
| New Game | 새 게임 |
| New Game + | 새 게임+ |
| Steve | 스티브 |
| Lem | 렘 |
| Ratskeller | 라츠켈러 |
| Pierce | 피어스 |
| Royal Air Force | 왕립 공군 |
| Final Retort | FINAL RETORT |
| Swift Reply | SWIFT REPLY |
| LANCER_01 | LANCER_01 |

Tone: natural spoken Korean. Proper names/callsigns transliterate.
Keep `#`, `{}`, `[]`, `<>`, `\n`, and markup/escape tokens exactly as in the English cell.
해요체 for formal/official contexts, 반말 for close/friendly relations as English implies.
## Fonts
- Noto Sans KR Regular (SIL Open Font License v1.1) by Google — clean sans-serif Korean font with full Hangul coverage.
- Used for rendering Hangul glyphs into the game's bitmap font texture atlas.
- Text font (fo_text_jap): em=40, cell height 79px. Contains 95 Latin + 11172 syllables + 94 Jamo = 11366 glyphs.
- Header font (fo_header_jap): em=60, cell height 119px. Contains 95 Latin + 7400 syllables + 94 Jamo = 7594 glyphs.
- Glyph sets are frequency-ordered (most common syllables prioritized) to maximize coverage within the 16384px GMImage height limit.

## Font fix (2026-10-21)
- Original fonts (build 1): 4096x9398/16216 textures exceeded GameMaker engine limit (~8192px), causing glyph misalignment.
- Fixed: textures constrained to 4096x974 (text) and 4096x2422 (header), well within safe limits.
- Additional bugs fixed: glyph paste position (offset is render cursor shift, not texture coordinate), Latin offset preservation, alpha-blending artifacts.
- 963 Hangul syllables (frequency-ordered from dialogue+UI needs + buffer) + 94 Jamo + 100 Latin = 1157 glyphs per font.
- Noto Sans KR Regular (SIL OFL v1.1) used for Hangul rendering.

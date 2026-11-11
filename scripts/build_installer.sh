#!/usr/bin/env bash
# 설치기 payload 생성 + Nuitka exe 빌드 (Windows 쪽 py 사용).
# 먼저 scripts/rebuild_all.sh 로 out/ 을 만든다 (패치된 Jet Lancer.exe, data.win, Dialogue/...).
# usage: PATCHED=<out 폴더> PRISTINE=<원본 폴더> scripts/build_installer.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/../../tools-l10n-ko/tools/build/installer"
PATCHED="${PATCHED:-$ROOT/out}"
PRISTINE="${PRISTINE:-$ROOT/backup}"
STAGE="$ROOT/build/payload"
NAME="$(python3 "$TOOLS/exe_name.py" "$ROOT/installer/config.template.json" "$ROOT")"  # {게임명}_{버전}_{yymmdd}_{커밋}
rm -rf "$ROOT/build"; mkdir -p "$STAGE"
python3 "$TOOLS/make_payload.py" --template "$ROOT/installer/config.template.json" \
  --out "$STAGE" --patched-dir "$PATCHED" --pristine-dir "$PRISTINE"
mkdir -p "$ROOT/dist"
# 이름에 커밋이 들어가므로 이전 빌드의 설치기를 지운다 (한 번에 하나만 배포). 실행 중이면 지워지지 않아 중단된다.
rm -f "$ROOT"/dist/*.exe || { echo "dist/*.exe 를 지울 수 없습니다. 실행 중인 설치기를 종료하세요." >&2; exit 1; }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$TOOLS/build.ps1")" \
  -Name "$NAME" -Payload "$(wslpath -w "$STAGE")" \
  -Config "$(wslpath -w "$STAGE/config.json")" -Out "$(wslpath -w "$ROOT/dist")"
# 폰트 라이선스(dist/LICENSES/)와 README 의 '사용 폰트' 섹션은 installer/fonts.json 에서 만든다
python3 "$TOOLS/ship_fonts.py" --fonts "$ROOT/installer/fonts.json" --repo "$ROOT" \
  --readme "$ROOT/installer/README.md" --dist "$ROOT/dist" --out-readme "$ROOT/build/README.merged.md"
# 배포용 README 는 installer/README.md (빌드/개발 안내가 들어 있으면 여기서 중단된다)
bash "$TOOLS/ship_readme.sh" "$ROOT/build/README.merged.md" "$ROOT/dist/README.md"
[ "$ROOT/dist/$NAME.exe" -nt "$TOOLS/installer.py" ] || { echo "dist/$NAME.exe 가 installer.py 보다 오래되었습니다 (빌드 실패?)" >&2; exit 1; }
echo "built: dist/$NAME.exe"

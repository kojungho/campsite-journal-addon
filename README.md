# 캠핑장 기록

Home Assistant에서 방문한 캠핑장을 남기고, 안드로이드 앱과 아이폰 홈 화면 웹앱에서도 같은 기록을 열어봅니다.

## Home Assistant 설치

1. 설정 → 앱(애드온) → 앱 스토어 → ⋮ → 저장소에 `https://github.com/kojungho/campsite-journal-addon` 추가.
2. **캠핑장 기록** 설치 → 시작 → **사이드바에 표시** 켜기.
3. 사이드바 **캠핑장 기록** 접속.

Home Assistant OS / Supervisor 필요. GitHub Actions에서 테스트 후 amd64 / aarch64 이미지를 빌드하여 GHCR에 배포합니다. HA에서는 이미 빌드한 이미지를 다운로드합니다.

## 기능

- 예약 플랫폼, 예약 링크 ↗, 캠핑장명, 위치, 지도 링크 ↗, 사이트명, 가격(원), 입실·퇴실·숙박일수, 메모.
- 목록 행을 눌러 상세정보 열기. 목록에서 숨긴 항목도 상세에는 유지.
- 사진 갤러리와 배치도 갤러리. ＋를 눌러 여러 장 첨부. 사진 클릭 시 확대, 사진 안 ×로 삭제.
- JPG, PNG, WebP, GIF, HEIC 지원. 방향 보정 후 최대 3200px JPG로 저장. 한 번에 64MB까지 첨부.
- 위치로 좌표 검색 / 위도·경도 직접 입력. 상세 지도와 전체 방문 지도. 지도 링크를 붙여넣고 좌표도 등록해야 지도 핀이 표시됩니다.
- 지도 및 위치 검색은 인터넷 연결 필요. 위치 검색 버튼을 누르면 입력한 이름·주소를 OpenStreetMap 검색 서비스에 전달합니다.
- 설정: 항목 표시 ON/OFF, ☰ 핸들로 마우스·터치 드래그 순서 이동. 키보드 위/아래 방향키 지원.
- PC / 모바일 별도 열 너비(최소 20px), 글자 크기(최소 8px), 셀 여백(최소 2px). 모바일 기준 700px.
- 전체 기록·사진 ZIP 백업. 기기 연결키는 백업에서 제외.

데이터: `/data/campsite-journal/journal.sqlite3`, 사진: 같은 디렉터리의 `photos/`. 재시작·업데이트 후 유지되고 HA 앱 백업에 포함됩니다.

## 자체 앱 연결 구성요소 설치

1. 앱 설치·연결에서 연결 ZIP을 받습니다.
2. `/config/custom_components/campsite_journal_bridge/`에 `__init__.py`, `manifest.json`을 넣습니다.
3. configuration.yaml에 아래 항목 추가 → 설정 검사 → HA 재시작.

```yaml
campsite_journal_bridge:
```

4. 앱 설치·연결의 주소를 `https://ha.badara.co.kr/campsite-journal/`로 설정하고 자체 앱 연결을 허용합니다.

기본 내부 주소는 `http://e1946121-campsite-journal:8098`입니다. 저장소 URL이 달라지면 backend_url을 실제 앱 hostname에 맞추세요. 별도 인터넷 포트는 열지 않습니다. 연결 구성요소는 캠핑장 기록 경로만 전달하고, 기기 연결키가 있어야 기록에 접근할 수 있습니다. HA 비밀번호는 자체 앱에 저장되지 않습니다. HA에서 기기를 해제하면 접근이 차단됩니다.

## 안드로이드 설치

1. HA → 캠핑장 기록 → **앱 설치·연결 → 안드로이드 APK 다운로드**.
2. 파일 앱에서 APK 열기 → 설치. 요청되면 이 출처의 앱 설치 허용. Android 10 이상 지원.
3. HA에서 기기 이름·안드로이드 선택 → **기기 연결 만들기**.
4. 앱에 기기 연결키 붙여넣기 또는 연결 버튼/QR 사용.
5. 홈 화면 **캠핑장 기록** 아이콘으로 접속.
6. 앱 설정에서 갤러리 / 파일 앱 선택. 기기마다 따로 저장됩니다.

서명된 APK는 GitHub 릴리스에서도 제공합니다. 공개 APK에는 HA 로그인 정보나 기기 연결키가 없습니다. 연결키는 Android Keystore로 암호화됩니다. APK 서명키는 소스에 포함되지 않습니다.

## 아이폰 / 아이패드 설치

1. HA에서 아이폰용 기기 연결 생성.
2. 연결 주소를 **Safari**로 열어 연결.
3. **공유 → 홈 화면에 추가 → 웹앱으로 열기 → 추가**.
4. 홈 화면 **캠핑장 기록** 아이콘으로 접속. iOS 17.2 이상 권장.
5. 설정에서 파일 모드는 **파일 선택**, 갤러리 모드는 **사진 보관함** 선택. iOS의 선택 메뉴 표시는 운영체제에서 결정합니다.

아이폰용은 홈 화면 웹앱(PWA)입니다. App Store 네이티브 앱은 아니며 인터넷·HA 연결이 필요합니다. 인증이 풀리면 기기 연결키로 다시 연결하세요. HA 앱에서는 파일 선택 방식으로 첨부합니다.

## 개발과 배포

```sh
python3 -m venv .venv
.venv/bin/pip install -r campsite_journal/requirements.txt
JOURNAL_DATA=./.local-data JOURNAL_HOST=127.0.0.1 .venv/bin/python campsite_journal/app.py
.venv/bin/python -m unittest discover -s tests -v
```

로컬 화면: http://127.0.0.1:8099. 운영 컨테이너 8099는 Ingress 프록시만 허용, 8098은 기기 인증 필요. 기기 관리 API는 HA Ingress에서만 사용 가능합니다.

이미지 업데이트: config.yaml 버전을 올리고 main push → Actions 성공 → HA 스토어 업데이트 확인. 최초 GHCR 패키지는 Public인지 확인하세요.

APK 빌드: SDK build-tools 36.1.0 / android-36, JDK 필요. `ANDROID_SDK_ROOT`, `CAMP_APK_BUILD_DIR`(소스 외부), `CAMP_APK_KEYSTORE`(소스 외부), `CAMP_APK_STOREPASS` 환경변수 설정 후 `android/build-apk.sh`. 기존 키를 유지해야 앱을 덮어써 업데이트할 수 있습니다.

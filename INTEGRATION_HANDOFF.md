# 캠핑 노트 통합 앱 인계

통합 앱 이름은 **캠핑 노트**, 내부 탭은 **캠핑장 기록 / 캠핑 장부**입니다.

## 개발 담당 위치
- 통합 앱·Android APK·업데이트·연결 화면·PWA: `kojungho/campsite-journal-addon` (이 저장소).
- 캠핑장 기록 기능: 이 저장소의 `campsite_journal/`.
- 캠핑 장부 기능·장부 API·장부 데이터: `kojungho/camp-ledger-addon`.
- 장부 쪽에서 통합 APK를 별도로 배포하거나 버전 번호를 따로 올리지 않습니다. 장부 전용 기존 앱은 별도 제품이며 통합 APK와 패키지가 다릅니다.

## 구성과 유지해야 할 계약
- 두 HA 애드온과 데이터베이스는 그대로 유지합니다. 통합 화면에서 각각을 iframe으로 열고 전환해 입력 상태를 유지합니다.
- 통합 진입 주소: https://ha.badara.co.kr/campsite-journal/hub
- 기록: `/campsite-journal/`, 장부: `/camp-ledger/` (같은 HTTPS 도메인).
- 기록 기기 인증 후 통합 화면을 엽니다. 장부 최초 접속은 장부에서 발급한 별도 기기 연결키가 필요합니다.
- 장부 연결 확인: GET `/camp-ledger/api/mobile/status`. 연결: POST `/camp-ledger/api/mobile/session`, JSON `{key: 연결키}`, 헤더 `X-Camp-Request: 1`. 인증은 HttpOnly `camp_device` 쿠키를 사용합니다. 키를 URL·localStorage·문서·저장소에 넣지 않습니다.
- 장부의 iframe 허용 정책과 동일 출처 연결을 유지하세요. CSP frame-ancestors / X-Frame-Options 변경 시 통합 화면 영향을 확인해야 합니다.
- Android 브리지 `CampLedgerNative`는 장부용, `CampsiteJournalNative`는 기록용입니다. 사진 선택·편집 상태를 각 브리지로 전달합니다. 편집 중 APK 업데이트가 끼어들지 않게 busy 상태를 유지합니다.
- 통합 탭 전환 요청은 부모에 `{type:'camp-switch', service:'journal' 또는 'ledger'}` 메시지를 보냅니다. 송신 시 정확한 origin을 지정하고 수신 시 origin과 iframe source를 검증합니다.

## Android와 iPhone
- Android 패키지 `co.kr.badara.campsitejournal`와 기존 서명을 유지합니다. 표시 이름만 캠핑 노트로 변경했습니다. 앱 시작 시 새 APK가 있으면 다운로드·설치 화면으로 안내합니다. 설치 완료에는 사용자 조작이 필요합니다.
- APK/버전 정보는 이 저장소의 GitHub Release 및 `campsite_journal/static/downloads/`에서 제공합니다. 서명키는 저장소에 없습니다.
- iPhone은 통합 주소를 Safari에서 홈 화면에 추가하는 PWA입니다. 네이티브 iOS 설치 파일이 아닙니다.
- 장부 웹 기능만 바뀌면 장부 애드온 배포로 반영됩니다. 통합 틀·Android 권한·브리지·APK 변경은 이 저장소에서 처리합니다.

## 배포 주의
- HA 애드온은 GitHub Actions의 사전 빌드 이미지가 성공적으로 공개된 후 업데이트합니다.
- 장부 로컬 체크아웃이 HA 설치 버전보다 뒤처질 수 있으므로 최신 원격 상태를 확인한 후 작업하세요. 구버전 로컬 코드를 설치하지 마세요.
- API·자동 테스트와 APK 컴파일·서명은 검증했습니다. 실제 휴대폰의 두 서비스 전환·사진 선택·설치는 별도 기기 확인이 필요합니다.

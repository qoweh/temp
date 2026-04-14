# URL Response Site 실행 가이드

## 1) 필요한 개발환경
- OS: Linux, macOS, 또는 Windows(WSL 포함)
- Python: 3.10 이상 (권장 3.12)
- 추가 패키지: 없음 (표준 라이브러리만 사용)

## 2) 실행 순서
1. 작업 경로 이동

```bash
cd /workspaces/temp/analyse
```

2. 실행 파일 문법 확인(선택)

```bash
python3 -m py_compile url_response_site.py
```

3. 서버 실행

```bash
python3 url_response_site.py
```

4. 브라우저 접속

```text
http://127.0.0.1:8010
```

## 3) 옵션
- 포트 변경:

```bash
PORT=8020 python3 url_response_site.py
```

- 바인딩 주소 변경:

```bash
HOST=0.0.0.0 python3 url_response_site.py
```

- URL별 요청 타임아웃(초) 변경:

```bash
FETCH_TIMEOUT_SEC=6 python3 url_response_site.py
```

## 4) 종료 방법
- 실행 터미널에서 `Ctrl+C`

## 5) 자주 발생하는 문제
- `OSError: [Errno 98] Address already in use`
  - 같은 포트를 이미 다른 프로세스가 사용 중입니다.
  - 해결: 다른 포트로 실행 (`PORT=8020 ...`) 또는 기존 프로세스를 종료합니다.

- 일부 URL이 느리거나 실패함
  - 외부 API 상태/네트워크 영향일 수 있습니다.
  - 화면의 `source`, `status`, `error`를 함께 확인하세요.

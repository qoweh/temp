#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import ssl
import textwrap
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
URL_FILE = BASE_DIR / "url.md"


@dataclass
class FetchResult:
    ok: bool
    status: int
    content_type: str
    elapsed_ms: int
    text: str
    error: str
    source: str


def load_urls() -> list[str]:
    if not URL_FILE.exists():
        return []

    urls: list[str] = []
    for line in URL_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
    return urls


def guess_fallback_file(url: str) -> Path | None:
    parsed = urlparse(url)
    if "getRoadTrafficInfoList" not in parsed.path:
        return None

    route_id = parse_qs(parsed.query).get("routeId", [""])[0].strip()
    if not route_id:
        return None

    candidates = sorted((BASE_DIR / "20260413").glob(f"gg_getRoadTrafficInfoList_{route_id}_*.xml"))
    if candidates:
        return candidates[-1]
    return None


def decode_bytes(raw: bytes, content_type: str) -> str:
    charset = "utf-8"
    match = re.search(r"charset=([^;]+)", content_type, flags=re.IGNORECASE)
    if match:
        charset = match.group(1).strip()

    for encoding in [charset, "utf-8", "euc-kr", "cp949", "latin1"]:
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_url(url: str, timeout_sec: int = 4) -> FetchResult:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; URL-Response-Site/1.0)"})
    ssl_context = ssl._create_unverified_context()
    started = time.time()

    try:
        with urlopen(req, timeout=timeout_sec, context=ssl_context) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            text = decode_bytes(raw, content_type)
            elapsed_ms = int((time.time() - started) * 1000)
            return FetchResult(
                ok=True,
                status=getattr(resp, "status", 200),
                content_type=content_type,
                elapsed_ms=elapsed_ms,
                text=text,
                error="",
                source="live",
            )
    except HTTPError as exc:
        raw = b""
        try:
            raw = exc.read()
        except Exception:
            raw = b""
        content_type = getattr(exc, "headers", {}).get("Content-Type", "") if getattr(exc, "headers", None) else ""
        text = decode_bytes(raw, content_type) if raw else ""
        elapsed_ms = int((time.time() - started) * 1000)
        return FetchResult(
            ok=False,
            status=exc.code,
            content_type=content_type,
            elapsed_ms=elapsed_ms,
            text=text,
            error=str(exc),
            source="live",
        )
    except URLError as exc:
        elapsed_ms = int((time.time() - started) * 1000)
        return FetchResult(
            ok=False,
            status=0,
            content_type="",
            elapsed_ms=elapsed_ms,
            text="",
            error=str(exc.reason),
            source="live",
        )
    except Exception as exc:
        elapsed_ms = int((time.time() - started) * 1000)
        return FetchResult(
            ok=False,
            status=0,
            content_type="",
            elapsed_ms=elapsed_ms,
            text="",
            error=str(exc),
            source="live",
        )


def summarize_value(value: object, max_len: int = 120) -> str:
    if value is None:
        text = "-"
    elif isinstance(value, (dict, list)):
        try:
            text = json.dumps(value, ensure_ascii=False)
        except Exception:
            text = str(value)
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def render_kv_table(title: str, rows: list[tuple[str, str]]) -> str:
    if not rows:
        return ""
    body = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in rows
    )
    heading = f"<h3>{html.escape(title)}</h3>" if title else ""
    return f"{heading}<div class='tbl-wrap'><table class='kv'><tbody>{body}</tbody></table></div>"


def render_data_table(title: str, columns: list[str], rows: list[list[str]], total_count: int) -> str:
    if not columns or not rows:
        return ""

    header = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")

    note = ""
    if total_count > len(rows):
        note = f"<p class='muted'>showing first {len(rows)} rows / total {total_count}</p>"

    heading = f"<h3>{html.escape(title)}</h3>" if title else ""
    return (
        f"{heading}{note}<div class='tbl-wrap'>"
        f"<table class='tbl'><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
        f"</div>"
    )


def pretty_xml_preview(text: str) -> str:
    try:
        root = ET.fromstring(text)
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode")
    except Exception:
        return text


def parse_xml_summary(text: str) -> tuple[list[str], str, str]:
    root = ET.fromstring(text)
    header_cd = root.findtext(".//headerCd", default="").strip()
    header_msg = root.findtext(".//headerMsg", default="").strip()

    row_candidates = [
        root.findall(".//itemList"),
        root.findall(".//item"),
        root.findall(".//row"),
    ]
    rows = next((cand for cand in row_candidates if cand), [])

    summary = [
        f"XML root: {root.tag}",
        f"headerCd: {header_cd or '-'}",
        f"headerMsg: {header_msg or '-'}",
        f"row count: {len(rows)}",
    ]

    parsed_parts: list[str] = []
    metadata = [
        ("root", root.tag),
        ("headerCd", header_cd or "-"),
        ("headerMsg", header_msg or "-"),
        ("row count", str(len(rows))),
    ]
    parsed_parts.append(render_kv_table("XML metadata", metadata))

    if rows:
        first_row = rows[0]
        columns: list[str] = []
        for child in list(first_row):
            col = child.tag.split("}")[-1]
            if col not in columns:
                columns.append(col)
            if len(columns) >= 10:
                break

        sample_rows: list[list[str]] = []
        for row in rows[:20]:
            row_map: dict[str, str] = {}
            for child in list(row):
                row_map[child.tag.split("}")[-1]] = summarize_value((child.text or "").strip())
            sample_rows.append([row_map.get(col, "-") for col in columns])

        parsed_parts.append(render_data_table("XML row preview", columns, sample_rows, len(rows)))

    pretty = pretty_xml_preview(text)[:12000]
    parsed_html = "".join(parsed_parts) or "<p class='muted'>No structured XML fields found.</p>"
    return summary, parsed_html, pretty


def parse_json_summary(text: str) -> tuple[list[str], str, str]:
    obj = json.loads(text)
    if isinstance(obj, dict):
        keys = ", ".join(list(obj.keys())[:15])
        summary = ["JSON object", f"top-level keys: {keys or '-'}"]
    elif isinstance(obj, list):
        summary = ["JSON array", f"item count: {len(obj)}"]
    else:
        summary = [f"JSON scalar: {type(obj).__name__}"]

    parts: list[str] = []
    if isinstance(obj, dict):
        scalar_rows: list[tuple[str, str]] = []
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                continue
            scalar_rows.append((key, summarize_value(value)))
            if len(scalar_rows) >= 15:
                break
        parts.append(render_kv_table("JSON scalar fields", scalar_rows))

        list_key = None
        for key, value in obj.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                list_key = key
                break
        if list_key is not None:
            records = obj[list_key]
            columns = list(records[0].keys())[:10]
            rows = []
            for record in records[:20]:
                rows.append([summarize_value(record.get(col)) for col in columns])
            parts.append(render_data_table(f"JSON list preview: {list_key}", columns, rows, len(records)))

    elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
        columns = list(obj[0].keys())[:10]
        rows = []
        for record in obj[:20]:
            rows.append([summarize_value(record.get(col)) for col in columns])
        parts.append(render_data_table("JSON array preview", columns, rows, len(obj)))
    else:
        parts.append(render_kv_table("JSON value", [("value", summarize_value(obj, max_len=800))]))

    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
    parsed_html = "".join(parts) or "<p class='muted'>No structured JSON preview available.</p>"
    return summary, parsed_html, pretty[:12000]


def parse_html_summary(text: str) -> tuple[list[str], str, str]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "(no title)"

    heading_matches = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", text, flags=re.IGNORECASE | re.DOTALL)
    headings: list[str] = []
    for raw_heading in heading_matches[:8]:
        cleaned = re.sub(r"<[^>]+>", " ", raw_heading)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            headings.append(cleaned)

    link_matches = re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, flags=re.IGNORECASE | re.DOTALL)
    links: list[tuple[str, str]] = []
    for href, label in link_matches[:8]:
        label_clean = re.sub(r"<[^>]+>", " ", label)
        label_clean = re.sub(r"\s+", " ", label_clean).strip() or "(no label)"
        links.append((label_clean, href.strip()))

    stripped = re.sub(r"<[^>]+>", " ", text)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    preview = stripped[:300]
    summary = [f"HTML document", f"title: {title}", f"text preview: {preview}"]

    blocks: list[str] = [render_kv_table("HTML metadata", [("title", title), ("text preview", preview)])]

    if headings:
        heading_items = "".join(f"<li>{html.escape(h)}</li>" for h in headings)
        blocks.append(f"<h3>Heading preview</h3><ol class='line-list'>{heading_items}</ol>")

    if links:
        link_rows = [(label, href) for label, href in links]
        blocks.append(render_kv_table("Link preview", link_rows))

    return summary, "".join(blocks), text[:12000]


def parse_plain_text_summary(text: str) -> tuple[list[str], str, str]:
    trimmed = text.strip()
    if not trimmed:
        return ["empty response body"], "<p class='muted'>Empty body.</p>", ""

    chunks: list[str] = []
    lines = [line.strip() for line in trimmed.splitlines() if line.strip()]
    source_lines = lines if len(lines) > 1 else [trimmed]
    for line in source_lines:
        wrapped = textwrap.wrap(line, width=100) or [line]
        chunks.extend(wrapped)
        if len(chunks) >= 120:
            break

    if len(chunks) > 120:
        chunks = chunks[:120]

    items = "".join(f"<li>{html.escape(line)}</li>" for line in chunks)
    summary = [f"plain text length: {len(trimmed)}", f"display lines: {len(chunks)}"]
    parsed_html = f"<h3>Text preview (wrapped)</h3><ol class='line-list'>{items}</ol>"
    return summary, parsed_html, trimmed[:12000]


def parse_text_payload(text: str, content_type: str) -> tuple[str, list[str], str, str]:
    trimmed = text.strip()
    if not trimmed:
        return "empty", ["empty response body"], "<p class='muted'>Empty body.</p>", ""

    if "json" in content_type.lower() or trimmed.startswith("{") or trimmed.startswith("["):
        try:
            summary, parsed_html, raw_preview = parse_json_summary(trimmed)
            return "json", summary, parsed_html, raw_preview
        except Exception:
            pass

    if "xml" in content_type.lower() or trimmed.startswith("<?xml") or trimmed.startswith("<ServiceResult"):
        try:
            summary, parsed_html, raw_preview = parse_xml_summary(trimmed)
            return "xml", summary, parsed_html, raw_preview
        except Exception:
            pass

    if "html" in content_type.lower() or "<html" in trimmed.lower() or "<!doctype html" in trimmed.lower():
        summary, parsed_html, raw_preview = parse_html_summary(trimmed)
        return "html", summary, parsed_html, raw_preview

    summary, parsed_html, raw_preview = parse_plain_text_summary(trimmed)
    return "text", summary, parsed_html, raw_preview


def collect_entries(urls: list[str]) -> list[dict]:
    timeout_sec = int(os.getenv("FETCH_TIMEOUT_SEC", "4"))
    entries: list[dict] = []
    for url in urls:
        result = fetch_url(url, timeout_sec=timeout_sec)

        # Fallback is only used when live fetch fails for known route traffic URLs.
        if not result.ok:
            fallback = guess_fallback_file(url)
            if fallback and fallback.exists():
                fallback_text = fallback.read_text(encoding="utf-8", errors="replace")
                result = FetchResult(
                    ok=False,
                    status=result.status,
                    content_type="application/xml",
                    elapsed_ms=result.elapsed_ms,
                    text=fallback_text,
                    error=result.error,
                    source=f"fallback:{fallback.relative_to(BASE_DIR)}",
                )

        payload_kind, summary_lines, parsed_html, raw_preview = parse_text_payload(result.text, result.content_type)
        entries.append(
            {
                "url": url,
                "ok": result.ok,
                "status": result.status,
                "content_type": result.content_type or "-",
                "elapsed_ms": result.elapsed_ms,
                "source": result.source,
                "error": result.error,
                "payload_kind": payload_kind,
                "summary_lines": summary_lines,
                "parsed_html": parsed_html,
                "raw_preview": raw_preview,
            }
        )

    return entries


def render_page(entries: list[dict]) -> str:
    cards: list[str] = []
    for idx, e in enumerate(entries, start=1):
        status_text = str(e["status"]) if e["status"] else "ERR"
        status_class = "ok" if e["ok"] else "bad"
        summary_items = "\n".join(f"<li>{html.escape(line)}</li>" for line in e["summary_lines"])

        error_html = ""
        if e["error"]:
            error_html = f"<p class='error'>error: {html.escape(e['error'])}</p>"

        cards.append(
            f"""
            <section class=\"card\">
              <h2>{idx}. <a href=\"{html.escape(e['url'])}\" target=\"_blank\" rel=\"noreferrer\">{html.escape(e['url'])}</a></h2>
              <p>
                <span class=\"badge {status_class}\">status {status_text}</span>
                <span class=\"meta\">kind: {html.escape(e['payload_kind'])}</span>
                <span class=\"meta\">source: {html.escape(e['source'])}</span>
                <span class=\"meta\">content-type: {html.escape(e['content_type'])}</span>
                <span class=\"meta\">elapsed: {e['elapsed_ms']} ms</span>
              </p>
              {error_html}
              <ul>{summary_items}</ul>
                            <details open>
                                <summary>show parsed view</summary>
                                <div class="parsed">{e['parsed_html']}</div>
                            </details>
                            <details>
                                <summary>show raw preview</summary>
                                <pre>{html.escape(e['raw_preview'])}</pre>
              </details>
            </section>
            """
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return textwrap.dedent(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>URL Response Viewer</title>
          <style>
            :root {{
              --bg: #f4f1ea;
              --panel: #fffdf8;
              --ink: #19222d;
              --muted: #49596d;
              --ok: #0f766e;
              --bad: #b42318;
              --line: #ded6c7;
            }}
            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              font-family: "Noto Sans", "Segoe UI", sans-serif;
              color: var(--ink);
              background: radial-gradient(circle at 20% 0%, #fff4d6 0%, var(--bg) 50%, #edf3f9 100%);
            }}
            .wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px 40px; }}
            h1 {{ margin: 0 0 8px; font-size: 30px; }}
            .intro {{ margin: 0 0 20px; color: var(--muted); }}
            .card {{
              background: var(--panel);
              border: 1px solid var(--line);
              border-radius: 14px;
              margin-bottom: 14px;
              padding: 14px;
              box-shadow: 0 6px 20px rgba(25, 34, 45, 0.06);
            }}
            h2 {{ margin: 0 0 8px; font-size: 17px; line-height: 1.4; word-break: break-all; }}
            a {{ color: #0a4b8f; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .badge {{
              display: inline-block;
              font-weight: 700;
              border-radius: 999px;
              padding: 3px 10px;
              margin-right: 8px;
              color: #fff;
              font-size: 12px;
            }}
            .ok {{ background: var(--ok); }}
            .bad {{ background: var(--bad); }}
            .meta {{ color: var(--muted); margin-right: 10px; font-size: 12px; }}
            .error {{ color: var(--bad); font-weight: 600; }}
            ul {{ margin-top: 8px; margin-bottom: 10px; }}
                        h3 {{ margin: 12px 0 8px; font-size: 14px; }}
                        .parsed {{ margin-top: 8px; }}
                        .tbl-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 10px; background: #fff; }}
                        table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
                        th, td {{ padding: 8px 10px; border-bottom: 1px solid #ece4d7; text-align: left; vertical-align: top; }}
                        th {{ background: #faf6ef; }}
                        .kv th {{ width: 220px; }}
                        .muted {{ margin: 6px 0; color: var(--muted); font-size: 12px; }}
                        .line-list {{ margin: 6px 0 8px 20px; padding: 0; }}
                        .line-list li {{ margin: 2px 0; }}
            pre {{
              margin: 10px 0 0;
              max-height: 360px;
              overflow: auto;
              background: #111827;
              color: #e5edf8;
              padding: 12px;
              border-radius: 10px;
              font-size: 12px;
              line-height: 1.4;
            }}
          </style>
        </head>
        <body>
          <main class="wrap">
            <h1>URL Response Viewer</h1>
            <p class="intro">generated at {now} | total urls: {len(entries)}</p>
            {''.join(cards)}
          </main>
        </body>
        </html>
        """
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ["/", "/index.html"]:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        urls = load_urls()
        entries = collect_entries(urls)
        page = render_page(entries).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, fmt: str, *args) -> None:
        # Keep terminal output small.
        return


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8010"))

    server = HTTPServer((host, port), Handler)
    print(f"Serving URL response viewer at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

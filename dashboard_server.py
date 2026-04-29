import csv
import html
import io
import json
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_PAGE_SIZE = 20


def format_timestamp(timestamp: int | str | None) -> str:
    try:
        value = int(timestamp or 0)
    except (TypeError, ValueError):
        return "-"

    if value <= 0:
        return "-"

    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))


def truncate_text(text: str, limit: int = 120) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."


def normalize_actor_label(item: dict) -> str:
    first_name = str(item.get("first_name", "") or "").strip()
    last_name = str(item.get("last_name", "") or "").strip()
    username = str(item.get("username", "") or "").strip()
    chat_id = item.get("chat_id", "")
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()

    if full_name and username:
        return f"{full_name} (@{username})"
    if full_name:
        return full_name
    if username:
        return f"@{username}"
    if chat_id:
        return f"member {chat_id}"
    return "member"


def load_logs(log_file: Path) -> dict:
    if not log_file.exists():
        return {}

    try:
        with log_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def build_search_text(item: dict) -> str:
    parts = [
        str(item.get("chat_id", "") or ""),
        str(item.get("user_id", "") or ""),
        str(item.get("username", "") or ""),
        str(item.get("first_name", "") or ""),
        str(item.get("last_name", "") or ""),
        str(item.get("last_message_preview", "") or ""),
    ]

    entries = item.get("entries")
    if isinstance(entries, list):
        for entry in entries[-10:]:
            if isinstance(entry, dict):
                parts.append(str(entry.get("text", "") or ""))

    return " ".join(parts).lower()


def filter_logs(logs: dict, query: str) -> list[dict]:
    items = [item for item in logs.values() if isinstance(item, dict)]
    items.sort(key=lambda item: int(item.get("updated_at", 0) or 0), reverse=True)

    normalized_query = query.strip().lower()
    if not normalized_query:
        return items

    return [item for item in items if normalized_query in build_search_text(item)]


def paginate_items(items: list[dict], page: int, page_size: int) -> tuple[list[dict], int, int]:
    safe_page_size = max(1, min(page_size, 100))
    total_items = len(items)
    total_pages = max(1, (total_items + safe_page_size - 1) // safe_page_size)
    safe_page = max(1, min(page, total_pages))
    start_index = (safe_page - 1) * safe_page_size
    end_index = start_index + safe_page_size
    return items[start_index:end_index], safe_page, total_pages


def summarize_chat(item: dict) -> dict:
    entries = item.get("entries")
    entry_count = len(entries) if isinstance(entries, list) else 0
    return {
        "chat_id": item.get("chat_id"),
        "user_id": item.get("user_id"),
        "username": item.get("username", ""),
        "first_name": item.get("first_name", ""),
        "last_name": item.get("last_name", ""),
        "label": normalize_actor_label(item),
        "entry_count": entry_count,
        "updated_at": item.get("updated_at", 0),
        "updated_at_text": format_timestamp(item.get("updated_at")),
        "last_message_preview": item.get("last_message_preview", ""),
    }


def serialize_chat_detail(item: dict) -> dict:
    entries = item.get("entries")
    if not isinstance(entries, list):
        entries = []

    return {
        "chat_id": item.get("chat_id"),
        "user_id": item.get("user_id"),
        "username": item.get("username", ""),
        "first_name": item.get("first_name", ""),
        "last_name": item.get("last_name", ""),
        "label": normalize_actor_label(item),
        "updated_at": item.get("updated_at", 0),
        "updated_at_text": format_timestamp(item.get("updated_at")),
        "entries": [
            {
                "at": entry.get("at", 0),
                "at_text": format_timestamp(entry.get("at")),
                "sender": entry.get("sender", ""),
                "type": entry.get("type", "text"),
                "text": entry.get("text", ""),
            }
            for entry in entries
            if isinstance(entry, dict)
        ],
    }


def export_logs_as_rows(items: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in items:
        entries = item.get("entries")
        if not isinstance(entries, list):
            entries = []

        if not entries:
            rows.append(
                {
                    "chat_id": item.get("chat_id", ""),
                    "user_id": item.get("user_id", ""),
                    "username": item.get("username", ""),
                    "first_name": item.get("first_name", ""),
                    "last_name": item.get("last_name", ""),
                    "actor_label": normalize_actor_label(item),
                    "updated_at": format_timestamp(item.get("updated_at")),
                    "entry_at": "",
                    "sender": "",
                    "type": "",
                    "text": "",
                }
            )
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            rows.append(
                {
                    "chat_id": item.get("chat_id", ""),
                    "user_id": item.get("user_id", ""),
                    "username": item.get("username", ""),
                    "first_name": item.get("first_name", ""),
                    "last_name": item.get("last_name", ""),
                    "actor_label": normalize_actor_label(item),
                    "updated_at": format_timestamp(item.get("updated_at")),
                    "entry_at": format_timestamp(entry.get("at")),
                    "sender": entry.get("sender", ""),
                    "type": entry.get("type", "text"),
                    "text": entry.get("text", ""),
                }
            )
    return rows


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server_version = "LuckySpinDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/":
            self._send_html(self.server.render_index_html())  # type: ignore[attr-defined]
            return

        if not self._is_authorized(query):
            self._send_json({"ok": False, "error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return

        if parsed.path == "/api/logs":
            self._handle_logs_list(query)
            return

        if parsed.path.startswith("/api/logs/"):
            self._handle_log_detail(parsed.path)
            return

        if parsed.path == "/api/export.json":
            self._handle_export_json(query)
            return

        if parsed.path == "/api/export.csv":
            self._handle_export_csv(query)
            return

        if parsed.path == "/healthz":
            self._send_json({"ok": True, "status": "healthy"})
            return

        self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return

    def _is_authorized(self, query: dict[str, list[str]]) -> bool:
        access_token = getattr(self.server, "access_token", "")  # type: ignore[attr-defined]
        if not access_token:
            return True

        auth_header = self.headers.get("Authorization", "")
        bearer_token = ""
        if auth_header.lower().startswith("bearer "):
            bearer_token = auth_header[7:].strip()

        query_token = (query.get("token") or [""])[0].strip()
        return bearer_token == access_token or query_token == access_token

    def _handle_logs_list(self, query: dict[str, list[str]]) -> None:
        search_query = (query.get("query") or [""])[0]
        page = self._to_int((query.get("page") or ["1"])[0], default=1)
        page_size = self._to_int((query.get("page_size") or [str(DEFAULT_PAGE_SIZE)])[0], default=DEFAULT_PAGE_SIZE)

        logs = load_logs(self.server.log_file)  # type: ignore[attr-defined]
        filtered = filter_logs(logs, search_query)
        page_items, current_page, total_pages = paginate_items(filtered, page, page_size)

        payload = {
            "ok": True,
            "query": search_query,
            "page": current_page,
            "page_size": max(1, min(page_size, 100)),
            "total_pages": total_pages,
            "total_items": len(filtered),
            "items": [summarize_chat(item) for item in page_items],
        }
        self._send_json(payload)

    def _handle_log_detail(self, path: str) -> None:
        chat_id = path.rsplit("/", 1)[-1].strip()
        logs = load_logs(self.server.log_file)  # type: ignore[attr-defined]
        item = logs.get(chat_id)
        if not isinstance(item, dict):
            self._send_json({"ok": False, "error": "Chat log not found"}, status=HTTPStatus.NOT_FOUND)
            return

        self._send_json({"ok": True, "item": serialize_chat_detail(item)})

    def _handle_export_json(self, query: dict[str, list[str]]) -> None:
        rows = self._get_export_rows(query)
        body = json.dumps({"ok": True, "count": len(rows), "rows": rows}, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="telegram-private-logs.json"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_export_csv(self, query: dict[str, list[str]]) -> None:
        rows = self._get_export_rows(query)
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "chat_id",
                "user_id",
                "username",
                "first_name",
                "last_name",
                "actor_label",
                "updated_at",
                "entry_at",
                "sender",
                "type",
                "text",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
        body = buffer.getvalue().encode("utf-8-sig")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="telegram-private-logs.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_export_rows(self, query: dict[str, list[str]]) -> list[dict]:
        search_query = (query.get("query") or [""])[0]
        chat_id = (query.get("chat_id") or [""])[0].strip()
        logs = load_logs(self.server.log_file)  # type: ignore[attr-defined]

        if chat_id:
            item = logs.get(chat_id)
            items = [item] if isinstance(item, dict) else []
        else:
            items = filter_logs(logs, search_query)

        return export_logs_as_rows(items)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body_text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _to_int(value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


class DashboardHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, log_file: Path, access_token: str):
        super().__init__(server_address, handler_class)
        self.log_file = log_file
        self.access_token = access_token

    def render_index_html(self) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Telegram Log Dashboard</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --panel: #fffaf2;
      --panel-strong: #f0e1c8;
      --line: #d7c3a3;
      --text: #2d2012;
      --muted: #6e5a46;
      --accent: #a44820;
      --accent-dark: #793012;
      --good: #245c3c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(164,72,32,.18), transparent 30%),
        linear-gradient(180deg, #f8f1e5 0%, #f3e7d6 100%);
      color: var(--text);
    }}
    .wrap {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(164,72,32,.95), rgba(121,48,18,.92));
      color: #fff4e8;
      padding: 24px;
      border-radius: 24px;
      box-shadow: 0 20px 50px rgba(90, 40, 15, .18);
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 32px;
    }}
    .hero p {{
      margin: 0;
      color: rgba(255,244,232,.86);
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(340px, 460px) 1fr;
      gap: 20px;
      margin-top: 20px;
    }}
    .authbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      margin-top: 16px;
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255,250,242,.16);
      border: 1px solid rgba(255,244,232,.18);
    }}
    .auth-form {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      flex: 1;
    }}
    .auth-form input {{
      max-width: 340px;
      background: rgba(255,255,255,.96);
    }}
    .auth-status {{
      font-size: 14px;
      color: rgba(255,244,232,.88);
    }}
    .panel {{
      background: rgba(255,250,242,.92);
      border: 1px solid rgba(215,195,163,.85);
      border-radius: 24px;
      padding: 18px;
      backdrop-filter: blur(10px);
      box-shadow: 0 16px 40px rgba(90, 40, 15, .08);
    }}
    .toolbar {{
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 12px;
      margin: 18px 0 0;
    }}
    input {{
      width: 100%;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 14px;
      font-size: 15px;
      color: var(--text);
      background: #fff;
    }}
    button, .linkbtn {{
      padding: 14px 16px;
      border: 0;
      border-radius: 14px;
      cursor: pointer;
      font-weight: 600;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #fff7ee;
      background: var(--accent);
    }}
    button:hover, .linkbtn:hover {{
      background: var(--accent-dark);
    }}
    .ghost {{
      background: var(--panel-strong);
      color: var(--text);
    }}
    .ghost:hover {{
      background: #e4d2b6;
    }}
    .meta {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 14px;
    }}
    .list {{
      display: grid;
      gap: 12px;
      margin-top: 16px;
    }}
    .card {{
      padding: 14px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: #fff;
      cursor: pointer;
      width: 100%;
      text-align: left;
      transition: transform .14s ease, box-shadow .14s ease;
    }}
    .card:hover {{
      transform: translateY(-1px);
      box-shadow: 0 12px 24px rgba(90, 40, 15, .08);
    }}
    .card.active {{
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(164,72,32,.15);
    }}
    .card h3 {{
      margin: 0;
      font-size: 18px;
      line-height: 1.3;
      color: var(--accent-dark);
    }}
    .card-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .card-subtitle {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }}
    .card-meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 12px;
      margin-top: 0;
      padding-top: 12px;
      border-top: 1px solid rgba(215,195,163,.75);
    }}
    .card-meta-item {{
      min-width: 0;
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(240,225,200,.28);
      min-height: 72px;
    }}
    .card-label {{
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .card-value {{
      color: var(--text);
      font-size: 14px;
      line-height: 1.4;
      word-break: break-word;
      font-weight: 600;
    }}
    .card-preview {{
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(248,241,229,.95), rgba(240,225,200,.32));
    }}
    .card-preview .card-value {{
      color: var(--muted);
      font-weight: 500;
    }}
    .detail-head {{
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    .detail-head h2 {{
      margin: 0;
      font-size: 24px;
    }}
    .chips {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .chip {{
      border-radius: 999px;
      padding: 8px 12px;
      background: var(--panel-strong);
      font-size: 13px;
      color: var(--text);
    }}
    .log-list {{
      display: grid;
      gap: 10px;
      max-height: 70vh;
      overflow: auto;
      padding-right: 4px;
    }}
    .log-item {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 14px;
      background: #fff;
    }}
    .log-item .top {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .log-item.member {{
      border-left: 5px solid #245c3c;
    }}
    .log-item.bot {{
      border-left: 5px solid var(--accent);
    }}
    .empty {{
      padding: 18px;
      border: 1px dashed var(--line);
      border-radius: 16px;
      color: var(--muted);
      background: rgba(255,255,255,.7);
    }}
    .pagination {{
      display: flex;
      gap: 10px;
      margin-top: 14px;
      align-items: center;
      flex-wrap: wrap;
    }}
    @media (max-width: 980px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
      .toolbar {{
        grid-template-columns: 1fr;
      }}
      .authbar {{
        align-items: stretch;
      }}
      .auth-form {{
        flex-direction: column;
        align-items: stretch;
      }}
      .auth-form input {{
        max-width: none;
      }}
      .card-meta {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 640px) {{
      .card-head {{
        flex-direction: column;
      }}
      .card-meta {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Telegram Private Log Dashboard</h1>
      <p>Cari member dengan chat ID, username, nama, user ID, atau potongan isi percakapan. Export log bisa JSON atau CSV.</p>
      <div class="authbar">
        <form id="tokenForm" class="auth-form">
          <input id="tokenInput" type="password" placeholder="Masukkan token dashboard">
          <button id="tokenSaveButton" type="submit">Simpan Token</button>
          <button id="tokenClearButton" type="button" class="ghost">Hapus Token</button>
        </form>
        <div class="auth-status" id="authStatus">Token belum diisi.</div>
      </div>
      <div class="toolbar">
        <input id="searchInput" placeholder="Cari chat ID / username / user ID / isi chat">
        <button id="searchButton">Cari</button>
        <button id="refreshButton" class="ghost">Refresh</button>
      </div>
      <div class="meta" id="summaryText">Memuat data...</div>
    </section>

    <section class="grid">
      <div class="panel">
        <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;">
          <strong>Daftar Chat</strong>
          <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <a class="linkbtn ghost" id="exportJsonButton" href="#">Export JSON</a>
            <a class="linkbtn ghost" id="exportCsvButton" href="#">Export CSV</a>
          </div>
        </div>
        <div class="list" id="chatList"></div>
        <div class="pagination">
          <button id="prevPageButton" class="ghost">Prev</button>
          <span id="pageText">Halaman 1/1</span>
          <button id="nextPageButton" class="ghost">Next</button>
        </div>
      </div>

      <div class="panel">
        <div class="detail-head">
          <div>
            <h2 id="detailTitle">Pilih chat</h2>
            <div class="meta" id="detailMeta">Belum ada chat yang dipilih.</div>
          </div>
          <div class="chips" id="detailChips"></div>
        </div>
        <div class="log-list" id="logList">
          <div class="empty">Klik salah satu chat di kiri untuk melihat detail percakapan.</div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const requiresToken = {str(bool(self.access_token)).lower()};
    let token = sessionStorage.getItem("dashboard_token") || "";
    let currentPage = 1;
    let totalPages = 1;
    let currentQuery = "";
    let activeChatId = "";
    let refreshTimer = null;

    function escapeHtml(value) {{
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }}

    async function fetchJson(url) {{
      const response = await fetch(url, {{
        headers: token ? {{ Authorization: "Bearer " + token }} : {{}}
      }});
      if (!response.ok) {{
        if (response.status === 401) {{
          throw new Error("TOKEN_REQUIRED");
        }}
        throw new Error("HTTP " + response.status);
      }}
      return response.json();
    }}

    function updateAuthStatus(message, isError = false) {{
      const node = document.getElementById("authStatus");
      node.textContent = message;
      node.style.color = isError ? "#ffd9c9" : "rgba(255,244,232,.88)";
    }}

    function syncTokenUi() {{
      document.getElementById("tokenInput").value = token;
      if (!requiresToken) {{
        updateAuthStatus("Dashboard ini tidak memerlukan token.");
        return;
      }}
      if (token) {{
        updateAuthStatus("Token tersimpan di sesi browser ini.");
      }} else {{
        updateAuthStatus("Token belum diisi.");
      }}
    }}

    async function downloadExport(format) {{
      const query = currentQuery ? "?query=" + encodeURIComponent(currentQuery) : "";
      const response = await fetch("/api/export." + format + query, {{
        headers: token ? {{ Authorization: "Bearer " + token }} : {{}}
      }});
      if (response.status === 401) {{
        updateAuthStatus("Token salah atau belum diisi.", true);
        throw new Error("TOKEN_REQUIRED");
      }}
      if (!response.ok) {{
        throw new Error("HTTP " + response.status);
      }}

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = format === "json" ? "telegram-private-logs.json" : "telegram-private-logs.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
    }}

    async function loadList(page = 1) {{
      currentPage = page;
      currentQuery = document.getElementById("searchInput").value.trim();
      const url = "/api/logs?page=" + currentPage + "&query=" + encodeURIComponent(currentQuery);
      const data = await fetchJson(url);

      totalPages = data.total_pages || 1;
      document.getElementById("summaryText").textContent =
        "Total hasil: " + data.total_items + " chat | Halaman " + data.page + "/" + data.total_pages;
      document.getElementById("pageText").textContent =
        "Halaman " + data.page + "/" + data.total_pages;
      document.getElementById("prevPageButton").disabled = data.page <= 1;
      document.getElementById("nextPageButton").disabled = data.page >= data.total_pages;

      const chatList = document.getElementById("chatList");
      chatList.innerHTML = "";
      if (!data.items.length) {{
        chatList.innerHTML = '<div class="empty">Tidak ada chat yang cocok dengan pencarian.</div>';
        return;
      }}

      for (const item of data.items) {{
        const card = document.createElement("button");
        card.type = "button";
        card.className = "card" + (String(item.chat_id) === String(activeChatId) ? " active" : "");
        card.innerHTML = `
          <div class="card-head">
            <div>
              <h3>${{escapeHtml(item.label)}}</h3>
              <div class="card-subtitle">Ringkasan chat member terbaru</div>
            </div>
          </div>
          <div class="card-preview">
            <span class="card-label">Preview</span>
            <div class="card-value">${{escapeHtml(item.last_message_preview || "-")}}</div>
          </div>
        `;
        card.addEventListener("click", () => loadDetail(item.chat_id));
        chatList.appendChild(card);
      }}
    }}

    function renderDetail(item) {{
      document.getElementById("detailTitle").textContent = item.label;
      document.getElementById("detailMeta").textContent =
        "Chat ID: " + item.chat_id + " | Update terakhir: " + item.updated_at_text;
      document.getElementById("detailChips").innerHTML = `
        <span class="chip">Username: ${{escapeHtml(item.username || "-")}}</span>
        <span class="chip">User ID: ${{escapeHtml(item.user_id || "-")}}</span>
        <span class="chip">Entries: ${{escapeHtml(item.entries.length)}}</span>
      `;

      const logList = document.getElementById("logList");
      logList.innerHTML = "";
      if (!item.entries.length) {{
        logList.innerHTML = '<div class="empty">Belum ada isi percakapan.</div>';
        return;
      }}

      for (const entry of item.entries.slice().reverse()) {{
        const node = document.createElement("div");
        node.className = "log-item " + (entry.sender === "member" ? "member" : "bot");
        node.innerHTML = `
          <div class="top">
            <strong>${{entry.sender === "member" ? "Member" : "Bot"}}</strong>
            <span>${{escapeHtml(entry.at_text)}} | ${{escapeHtml(entry.type)}}</span>
          </div>
          <div>${{escapeHtml(entry.text || "-")}}</div>
        `;
        logList.appendChild(node);
      }}
    }}

    async function loadDetail(chatId) {{
      activeChatId = String(chatId);
      await loadList(currentPage);
      const data = await fetchJson("/api/logs/" + encodeURIComponent(chatId));
      renderDetail(data.item);
    }}

    async function refreshDashboardData() {{
      await loadList(currentPage);
      if (!activeChatId) {{
        return;
      }}

      const data = await fetchJson("/api/logs/" + encodeURIComponent(activeChatId));
      renderDetail(data.item);
    }}

    function startAutoRefresh() {{
      if (refreshTimer) {{
        clearInterval(refreshTimer);
      }}
      refreshTimer = setInterval(() => {{
        refreshDashboardData().catch((error) => {{
          if (error.message === "TOKEN_REQUIRED") {{
            updateAuthStatus("Token salah atau belum diisi.", true);
          }}
        }});
      }}, 5000);
    }}

    async function submitToken(event) {{
      event.preventDefault();
      token = document.getElementById("tokenInput").value.trim();
      if (token) {{
        sessionStorage.setItem("dashboard_token", token);
      }} else {{
        sessionStorage.removeItem("dashboard_token");
      }}
      syncTokenUi();
      try {{
        await loadList(1);
      }} catch (error) {{
        if (error.message === "TOKEN_REQUIRED") {{
          updateAuthStatus("Token salah atau belum diisi.", true);
          return;
        }}
        updateAuthStatus("Gagal memverifikasi token: " + error.message, true);
      }}
    }}

    document.getElementById("searchButton").addEventListener("click", () => loadList(1));
    document.getElementById("refreshButton").addEventListener("click", () => loadList(currentPage));
    document.getElementById("tokenForm").addEventListener("submit", submitToken);
    document.getElementById("tokenClearButton").addEventListener("click", () => {{
      token = "";
      sessionStorage.removeItem("dashboard_token");
      syncTokenUi();
    }});
    document.getElementById("exportJsonButton").addEventListener("click", async (event) => {{
      event.preventDefault();
      try {{
        await downloadExport("json");
      }} catch (error) {{
        if (error.message !== "TOKEN_REQUIRED") {{
          updateAuthStatus("Gagal export JSON: " + error.message, true);
        }}
      }}
    }});
    document.getElementById("exportCsvButton").addEventListener("click", async (event) => {{
      event.preventDefault();
      try {{
        await downloadExport("csv");
      }} catch (error) {{
        if (error.message !== "TOKEN_REQUIRED") {{
          updateAuthStatus("Gagal export CSV: " + error.message, true);
        }}
      }}
    }});
    document.getElementById("prevPageButton").addEventListener("click", () => {{
      if (currentPage > 1) {{
        loadList(currentPage - 1);
      }}
    }});
    document.getElementById("nextPageButton").addEventListener("click", () => {{
      if (currentPage < totalPages) {{
        loadList(currentPage + 1);
      }}
    }});
    document.getElementById("searchInput").addEventListener("keydown", (event) => {{
      if (event.key === "Enter") {{
        loadList(1);
      }}
    }});

    syncTokenUi();
    startAutoRefresh();
    loadList(1).catch((error) => {{
      if (error.message === "TOKEN_REQUIRED") {{
        document.getElementById("summaryText").textContent = requiresToken
          ? "Masukkan token dashboard untuk memuat data."
          : "Gagal memuat dashboard: token diperlukan.";
        updateAuthStatus("Token salah atau belum diisi.", true);
        return;
      }}
      document.getElementById("summaryText").textContent = "Gagal memuat dashboard: " + error.message;
    }});
  </script>
</body>
</html>"""


def start_dashboard_server(
    log_file: str | Path,
    host: str | None = None,
    port: int | None = None,
    access_token: str | None = None,
) -> DashboardHTTPServer:
    resolved_host = host or os.getenv("DASHBOARD_HOST", "0.0.0.0")
    resolved_port = int(port or os.getenv("PORT", os.getenv("DASHBOARD_PORT", "8080")))
    resolved_token = (access_token if access_token is not None else os.getenv("DASHBOARD_TOKEN", "")).strip()
    resolved_log_file = Path(log_file)

    server = DashboardHTTPServer(
        (resolved_host, resolved_port),
        DashboardRequestHandler,
        log_file=resolved_log_file,
        access_token=resolved_token,
    )

    thread = threading.Thread(target=server.serve_forever, name="dashboard-http-server", daemon=True)
    thread.start()
    return server

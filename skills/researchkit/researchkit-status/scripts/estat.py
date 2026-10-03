"""estat.py - e-Stat（政府統計の総合窓口）のファイルの一覧を読み、表を取得する部品（researchkit.py estat が使う）

e-Stat のファイルの一覧（https://www.e-stat.go.jp/stat-search/files?...）は、政府統計コード → 統計の分類（tstat、
tclass1〜）→ 表（statInfId）の順にたどる。ページの HTML を読み、次をする。
- 分類の一覧: 下の階層へのリンクと、その名前・件数・公開（更新）日
- 表の一覧: statInfId、表番号、題名、調査年月、公開（更新）日、取得できる形式（fileKind）
- 取得: statInfId と fileKind から file-download の URL を作り、保存し、中身の形式（xls、xlsx、csv、pdf、zip、html）を見分ける
API キーは要らない。標準ライブラリだけで書く（Python 3.9 以上）。
"""

from __future__ import annotations

import hashlib
import html
import re
import urllib.request
from pathlib import Path

BASE = "https://www.e-stat.go.jp"
FILES = BASE + "/stat-search/files"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
KIND_NAMES = {"0": "Excel", "1": "CSV", "2": "PDF", "3": "DB", "4": "Excel(統計表)"}


def text(fragment: str) -> str:
    """HTML の断片を、タグを除いた 1 行の文字にする。"""
    fragment = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def list_url(target: str) -> str:
    """政府統計コード（8 桁）、files の URL、/stat-search/ で始まるパスのどれかを、一覧の URL にする。"""
    t = target.strip()
    if re.fullmatch(r"\d{8}", t):
        return f"{FILES}?page=1&toukei={t}"
    if t.startswith("/"):
        return BASE + t
    if t.startswith("http"):
        return t
    raise ValueError(f"政府統計コード（8 桁）か e-Stat の一覧の URL を指定する: {target}")


def download_url(stat_inf_id: str, kind: str) -> str:
    return f"{BASE}/stat-search/file-download?statInfId={stat_inf_id}&fileKind={kind}"


def fetch(url: str, timeout: float = 60.0) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - e-Stat の URL だけを渡す
        return r.status, r.read(), r.headers.get("Content-Type", "")


def parse_files(page: str) -> list[dict[str, str]]:
    """表の一覧のページから、表ごとの statInfId・表番号・題名・調査年月・公開日・形式を取り出す。

    表は <article class="stat-dataset_list-item"> の単位で並ぶ。表を持たない article は、続く表の見出し（グループ名）。
    """
    out: list[dict[str, str]] = []
    group = ""
    for art in re.split(r'<article class="stat-dataset_list-item', page)[1:]:
        art = art.split("</article>")[0]
        ids = re.findall(r"statInfId=(\d+)", art)
        if not ids:
            g = text(art.split(">", 1)[-1])
            if g:
                group = g
            continue
        kinds = sorted(set(re.findall(r"statInfId=\d+&(?:amp;)?fileKind=(\d)", art)))
        t = text(art.split(">", 1)[-1])
        no = re.search(r"表番号\s*(\S+)", t)
        ym = re.search(r"調査年月\s*(.+?)\s*公開（更新）日", t)
        day = re.search(r"公開（更新）日\s*(\d{4}-\d{2}-\d{2})", t)
        title = t
        title = re.sub(r"^.*?表番号\s*\S+\s*", "", title) if no else title
        title = re.split(r"\s*調査年月", title)[0].strip()
        if title in ("", "統計表") and group:
            title = group
        if any(r["statInfId"] == ids[0] for r in out):
            continue
        out.append({
            "statInfId": ids[0],
            "kinds": ",".join(kinds),
            "no": no.group(1) if no else "",
            "title": title,
            "period": ym.group(1).strip() if ym else "",
            "date": day.group(1) if day else "",
            "group": group,
        })
    return out


CYCLES = ("年次", "年度次", "月次", "四半期", "半年次", "不定期", "一回限り", "隔年", "その他")
_NAMED = re.compile(r"([^\[\]]+?)\s*\[([\d,]+)件\]")
_DATE = re.compile(r"公開（更新）日\s*(\d{4}-\d{2}-\d{2})")


def _clean_name(name: str) -> str:
    """名前の前に残った、前の行の件数・日付・印を落とす。"""
    name = re.split(r"公開（更新）日\s*\d{4}-\d{2}-\d{2}|\d[\d,]*件", name)[-1]
    return re.sub(r"^(新着|更新)\s*", "", name.strip()).strip()


def parse_classes(page: str) -> list[dict[str, str]]:
    """分類の一覧のページから、下の階層の一覧へのリンクと、その名前・件数・公開日を取り出す。

    2 つの形を読む。(1) リンクが「名前 [件数] … 公開（更新）日 日付」を包む形（政府統計コードのページ）。
    (2) 名前と件数がリンクの前にあり、リンクの文字は周期（年度次など）の形（分類のページ）。件数の分からないリンクは出さない。
    """
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    prev = 0
    for m in re.finditer(r'<a\b[^>]*href="(/stat-search/files\?[^"]+)"[^>]*>(.*?)</a>', page, re.S):
        url = html.unescape(m.group(1))
        before = text(page[prev:m.start()])
        inner = text(m.group(2))
        prev = m.end()
        if "tstat=" not in url or url in seen or "stat_infid=" in url:
            continue
        found = _NAMED.search(inner)
        name, count = (_clean_name(found.group(1)), found.group(2)) if found else ("", "")
        if not name or name in CYCLES:
            last = _NAMED.findall(before)
            if last:
                name = _clean_name(last[-1][0])
                count = count or last[-1][1]
        if not count:
            continue
        seen.add(url)
        day = _DATE.findall(inner) or _DATE.findall(before)
        cycle = inner.split()[0] if inner.split() and inner.split()[0] in CYCLES else ""
        out.append({"name": name[-80:], "cycle": cycle, "count": count, "date": day[-1] if day else "", "url": url})
    return out


def detect_format(data: bytes) -> str:
    """中身の先頭の数バイトから形式を見分ける。"""
    head = data[:8]
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "xls"
    if head.startswith(b"PK"):
        return "xlsx" if b"xl/" in data[:4000] or b"[Content_Types]" in data[:4000] else "zip"
    if head.startswith(b"%PDF"):
        return "pdf"
    low = data[:512].lower()
    if b"<html" in low or b"<!doctype html" in low:
        return "html"
    return "csv"


def save(stat_inf_id: str, kind: str, out: Path) -> dict[str, str]:
    """表を取得して保存し、形式・大きさ・SHA-256 を返す。中身が HTML（エラーのページ）なら保存しない。"""
    url = download_url(stat_inf_id, kind)
    status, data, ctype = fetch(url)
    fmt = detect_format(data)
    info = {"url": url, "http": str(status), "bytes": str(len(data)), "format": fmt, "content_type": ctype}
    if fmt == "html":
        info["error"] = "中身が HTML（表ではない）。statInfId と fileKind を確かめる"
        return info
    ext = out.suffix.lower().lstrip(".")
    if ext != fmt:
        # e-Stat は xlsx を .xls の名前で配ることがある。中身に合う拡張子で保存する（中身は変えない）
        info["warning"] = f"指定の拡張子 .{ext or '（なし）'} と中身の形式 {fmt} が違うので、.{fmt} で保存した"
        out = out.with_suffix(f".{fmt}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    info["path"] = str(out)
    info["sha256"] = hashlib.sha256(data).hexdigest()
    return info

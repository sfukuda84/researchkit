"""estat.py（e-Stat の一覧の読み取り）のテスト。ネットワークには出ない。HTML は e-Stat のページの形を縮めたもの。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "researchkit" / "researchkit-status" / "scripts"))
import estat  # noqa: E402

# 政府統計コードのページ: リンクが「名前 [件数] … 公開（更新）日」を包む形
TOUKEI_PAGE = """
<div class="stat-search_result-list js-items">
 <a href="/stat-search/files?page=1&amp;toukei=00200531&amp;layout=dataset" class="sg-btn">一覧形式で表示</a>
 <a href="/stat-search/files?page=1&amp;toukei=00200531&amp;tstat=000001226583" class="stat-link_text js-tstat_link">
  <ul><li><div><span class="stat-newinfo-icon"><span>新着</span></span>
  <span class="stat-title"><span> 労働力調査（公表資料、時系列結果など）<span class="stat-pc">[17,824件]</span></span></span>
  <span class="stat-date"><span class="stat-sp">17,824件</span><span class="stat-sp">&nbsp;&nbsp;公開（更新）日&nbsp;</span>2026-10-02</span>
  </div></li></ul></a>
 <a href="/stat-search/files?page=1&amp;toukei=00200531&amp;tstat=000001226891" class="stat-link_text js-tstat_link">
  <ul><li><div><span class="stat-title"><span> 労働力調査年報<span class="stat-pc">[2,091件]</span></span></span>
  <span class="stat-date"><span class="stat-sp">2,091件</span><span class="stat-sp">公開（更新）日&nbsp;</span>2026-05-29</span>
  </div></li></ul></a>
</div>
"""

# 分類のページ: 名前と件数がリンクの前にあり、リンクの文字は周期
TSTAT_PAGE = """
<li><div><span class="stat-title">令和７年度食料需給表（概算）
 <span class="stat-pc">[1件]</span></span><span class="stat-date"><span class="stat-sp">1件</span></span></div>
 <ul class="stat-matter6"><li><a href="/stat-search/files?page=1&amp;toukei=00500300&amp;tstat=000001017950&amp;cycle=8&amp;tclass1=000001034325&amp;tclass2=000001245617&amp;layout=datalist&amp;tclass3val=0" class="stat-link_text">
 年度次 [1件] 1件 公開（更新）日 2026-08-07</a></li></ul></li>
<li><div><span class="stat-title">令和６年度食料需給表
 <span class="stat-pc">[99件]</span></span></div>
 <ul class="stat-matter6"><li><a href="/stat-search/files?page=1&amp;toukei=00500300&amp;tstat=000001017950&amp;cycle=8&amp;tclass1=000001032890&amp;tclass2=000001241316&amp;layout=datalist&amp;tclass3val=0" class="stat-link_text">
 年度次 [99件] 99件 公開（更新）日 2026-08-07</a></li></ul></li>
"""

# 表の一覧のページ
FILES_PAGE = """
<div class="stat-dataset_list-body">
 <article class="stat-dataset_list-item"><div class="stat-dataset_list-main"><ul class="stat-dataset_list-group">
  <li class="stat-dataset_list-group-item">項目別累年表</li></ul></div></article>
 <article class="stat-dataset_list-item"><div class="stat-dataset_list-main"><ul class="stat-dataset_list-detail">
  <li><span class="stat-sp">表番号</span> 2</li>
  <li><a href="/stat-search/files?page=1&amp;stat_infid=000040422798" class="stat-link_text js-data">国内生産量</a>
  <div><span class="stat-sp">調査年月&nbsp;&nbsp;</span> 2024年度</div>
  <div><span class="stat-sp">公開（更新）日&nbsp;&nbsp;</span>2026-03-13</div>
  <a href="/stat-search/file-download?statInfId=000040422798&fileKind=1" data-file_type="CSV">CSV</a>
  <a href="/stat-search/file-download?statInfId=000040422798&amp;fileKind=4" data-file_type="EXCEL">Excel</a>
  </li></ul></div></article>
 <article class="stat-dataset_list-item"><div class="stat-dataset_list-main"><ul class="stat-dataset_list-detail">
  <li><a href="/stat-search/files?page=1&amp;stat_infid=000040482858" class="stat-link_text js-data">統計表</a>
  <div><span class="stat-sp">調査年月&nbsp;&nbsp;</span> 2025年度</div>
  <div><span class="stat-sp">公開（更新）日&nbsp;&nbsp;</span>2026-08-07</div>
  <a href="/stat-search/file-download?statInfId=000040482858&fileKind=0">Excel</a>
  </li></ul></div></article>
</div>
"""


class EstatTest(unittest.TestCase):
    def test_list_url(self) -> None:
        self.assertEqual(estat.list_url("00500300"), "https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00500300")
        self.assertTrue(estat.list_url("/stat-search/files?x=1").startswith("https://www.e-stat.go.jp/stat-search/"))
        with self.assertRaises(ValueError):
            estat.list_url("abc")

    def test_classes_wrapped_by_link(self) -> None:
        rows = estat.parse_classes(TOUKEI_PAGE)
        self.assertEqual([r["name"] for r in rows], ["労働力調査（公表資料、時系列結果など）", "労働力調査年報"])
        self.assertEqual(rows[0]["count"], "17,824")
        self.assertEqual(rows[0]["date"], "2026-10-02")
        self.assertTrue(rows[1]["url"].endswith("tstat=000001226891"))

    def test_classes_named_before_link(self) -> None:
        rows = estat.parse_classes(TSTAT_PAGE)
        self.assertEqual([r["name"] for r in rows], ["令和７年度食料需給表（概算）", "令和６年度食料需給表"])
        self.assertEqual([r["count"] for r in rows], ["1", "99"])
        self.assertEqual(rows[0]["cycle"], "年度次")
        self.assertEqual(rows[1]["date"], "2026-08-07")

    def test_files(self) -> None:
        rows = estat.parse_files(FILES_PAGE)
        self.assertEqual([r["statInfId"] for r in rows], ["000040422798", "000040482858"])
        first = rows[0]
        self.assertEqual((first["no"], first["title"], first["period"], first["date"], first["kinds"]),
                         ("2", "国内生産量", "2024年度", "2026-03-13", "1,4"))
        self.assertEqual(first["group"], "項目別累年表")
        # 題名が「統計表」だけのときは、見出し（グループ）の名前を使う
        self.assertEqual(rows[1]["title"], "項目別累年表")

    def test_detect_format(self) -> None:
        self.assertEqual(estat.detect_format(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest"), "xls")
        self.assertEqual(estat.detect_format(b"PK\x03\x04" + b"[Content_Types].xml xl/workbook.xml"), "xlsx")
        self.assertEqual(estat.detect_format(b"PK\x03\x04" + b"data.csv"), "zip")
        self.assertEqual(estat.detect_format(b"%PDF-1.7"), "pdf")
        self.assertEqual(estat.detect_format(b"<!DOCTYPE html><html>"), "html")
        self.assertEqual(estat.detect_format("統計名：,食料需給表".encode("cp932")), "csv")


if __name__ == "__main__":
    unittest.main()

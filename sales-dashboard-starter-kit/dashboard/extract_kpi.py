#!/usr/bin/env python3
"""個人予実シートの gviz CSV から自分のブロックを抽出して kpi_raw.json を書き出す。

これは特定のスプレッドシートのレイアウト（列位置・見出し文言）に合わせた実装例です。
自分のスプレッドシートに合わせて PERSON / SHEET_HEADER_MARKER / RANGES を書き換えてください
（下の「⚠️ ここを自分のシートに合わせて書き換える」を参照）。書き換え方は README.md の
「④ 個人予実データの抽出をカスタマイズする」に詳しく書いています。

使い方:
  python3 dashboard/extract_kpi.py [個人予実CSV]
  # 省略時は ~/Downloads/data*.csv の最新を使用

出力: dashboard/kpi_raw.json  {"months":[...12], "blocks":{指標:{目標/実績/差分/達成率/月日数進捗差分率:[...12]}}}
"""
import csv, json, os, sys, glob, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

# ⚠️ ここを自分のシートに合わせて書き換える -----------------------------
PERSON = '岩野'                        # 案件管理CSVの --person と同じ値にする
SHEET_HEADER_MARKER = 'FY27｜予実管理'  # 月見出し行を探すための目印文字列（行内にこの文字列を含む行を探す）
# 指標ごとの探索範囲（行番号）。シートが変わったら合わせて調整する。
# 範囲内で最初に「col index 3 が PERSON と一致する行」がその指標の担当者ブロック先頭とみなす。
RANGES = {
    '新規開業室数': (16, 46), '契約室数': (54, 84), '口頭合意室数': (94, 122),
    'リード室数': (134, 162), '案件獲得数': (178, 200),
}
# --------------------------------------------------------------------

src = sys.argv[1] if len(sys.argv) > 1 else max(
    glob.glob(os.path.expanduser('~/Downloads/data*.csv')) +
    glob.glob(os.path.expanduser('~/Downloads/個人予実*.csv')) +
    glob.glob(os.path.expanduser('~/Downloads/*予実*.csv')),
    key=os.path.getmtime, default='')
if not src or not os.path.exists(src):
    sys.exit('個人予実CSVが見つかりません。引数で渡してください。')
print('src:', src)

rows = list(csv.reader(open(src, encoding='utf-8')))
hdr = next(i for i, r in enumerate(rows) if any(SHEET_HEADER_MARKER in c for c in r))
this_year = datetime.date.today().year
months = [c for c in rows[hdr] if c.startswith((f'{this_year}/', f'{this_year+1}/', f'{this_year-1}/'))][:12]
mcols = [i for i, c in enumerate(rows[hdr]) if c in months][:12]

FIELDS = [(1, '目標'), (2, '実績'), (3, '差分'), (4, '達成率'), (5, '月日数進捗差分率')]

blocks = {}
for metric, (lo, hi) in RANGES.items():
    iw = next((i for i in range(lo, min(hi, len(rows)))
               if len(rows[i]) > 3 and rows[i][3].strip() == PERSON), None)
    if iw is None:
        sys.exit(f'{metric}: {PERSON}のブロックが範囲 {lo}-{hi} で見つかりません。RANGES を調整してください。')
    d = {}
    for off, key in FIELDS:
        r = rows[iw + off]
        lbl = (r[3].strip() if len(r) > 3 else '') or (r[4].strip() if len(r) > 4 else '')
        if key not in lbl:
            sys.exit(f'{metric} 行{iw + off}: ラベル不一致（期待 {key} / 実際 {lbl!r}）')
        d[key] = [r[c] if c < len(r) else '' for c in mcols]
    blocks[metric] = d
    print(f'  {metric:8} row{iw}  {d["実績"][0]}/{d["目標"][0]} ({d["達成率"][0]})')

json.dump({'months': months, 'blocks': blocks},
          open(f'{ROOT}/kpi_raw.json', 'w'), ensure_ascii=False, indent=1)
print(f'-> {ROOT}/kpi_raw.json  ({len(blocks)} blocks)')

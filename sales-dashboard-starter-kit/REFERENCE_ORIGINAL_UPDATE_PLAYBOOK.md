---
name: update-sales-dashboard
description: 「セールスアクション台帳」ダッシュボード（岩野希美さんの営業アクション・成果管理 Artifact）を最新データで更新する。隔週（2週間に1回）実行。名刺CSV・Googleカレンダー・2つのGoogleスプレッドシートからデータを取り直し、dashboard/build.py で再生成して同じ Artifact URL に再パブリッシュする。「ダッシュボード更新して」「営業台帳を更新」等で起動。
---

# セールスアクション台帳の更新手順

対象 Artifact: `https://claude.ai/code/artifact/e19c2c28-d5b6-4c9e-ab86-55b5b2ca007b`
プロジェクト: `/Users/iwanonozomi/売り物件整理`
関連メモリ: `[[sales-dashboard]]`

4つのデータソースを更新 → `dashboard/build.py` で組み立て → **同じ URL に**再パブリッシュ、の順。
非公開データ（カレンダー・スプレッドシート）は **Claude in Chrome**（ログイン済みの実 Chrome）で取得する。

---

## ① 名刺データ（クライアント属性）

ユーザーに名刺管理ツールから最新の名刺CSVをエクスポートして `~/Downloads/` に置いてもらう
（ファイル名例: `名刺出力YYYYMMDD_HHMMSS.csv`、UTF-8 BOM、ヘッダは `会社名,部署名,役職,氏名,郵便番号(1),住所(1)［全て］,...,名刺所有者ユーザID`）。
`build.py` は `~/Downloads/名刺出力*.csv` の最新を自動採用。無ければ既存ファイルのままでも可。

## ② 営業アクション数（Googleカレンダー）

Claude in Chrome で `nozomi.iwano@unito.me` のカレンダーから**当月**の予定を取得する。

1. 各キーワードで検索ビューを開く（結果はスクロールで追加読み込み。200件上限だが前後2〜3か月なので当月は必ず収まる）:
   - `https://calendar.google.com/calendar/u/0/r/search?q=往訪`
   - `https://calendar.google.com/calendar/u/0/r/search?q=来社`
   - `https://calendar.google.com/calendar/u/0/r/search?q=meets`
2. 各ページで下記JSを実行し、`[data-eventid]` の `aria-label` を収集:
   ```js
   [...document.querySelectorAll('[data-eventid]')].map(e=>e.getAttribute('aria-label')).filter(Boolean)
   ```
   aria-label 例: `午後2時～午後3時、「（往訪）◯◯様」、岩野希美、場所…、2026年 8月 4日`
3. **当月分だけ**に絞り、**自分のカレンダーの予定のみ**採用する:
   - `YYYY年 M月`（当月）を含む
   - `カレンダー:` を含まない = 岩野本人のカレンダー（`カレンダー: 小川小次郎` 等は同僚の共有カレンダーなので除外）
   - 件名（「」内）が実際に `往訪` / `来社` / `meets` を含むもの（`来客` などの別語は除外）
   - 研修・勉強会（例:「(meets)近藤塾…」）は件名に meets を含むが営業アクションではない。**明細には残しつつユーザーに要確認**（今は計上に含めている）。
   - **検索ビューの取得漏れに注意**: `q=来社` は履歴が多く結果ウィンドウ（〜400件）が当月後半まで届かないことがある（`q=往訪`/`q=meets` は数か月先まで届く）。月後半は `r/agenda/YYYY/M/DD` や週表示で補完し、`最大日付 < 月末` なら未取得分がある旨を報告する。
4. `dashboard/meetings.json` を配列で書き出す:
   ```json
   [{"type":"往訪","date":"2026-08-04","title":"（往訪）サンケイビル 山崎様","status":"承諾","daito":false}]
   ```
   - `type`: `往訪` | `来社` | `meets`
   - `status`: `承諾` | `辞退` | `出欠確認が必要` | `""`
   - `daito`: **顧客が大東建託株式会社なら `true`**（明細には残すが件数に計上しない）
   - 月間目標はコード側で固定（アポ30件／ホット案件5件）

## ③ 個人予実（岩野）

スプレッドシート `1enM8QTz45P1NKSjX4pVqTIXOhB-S8qKnjr4sHKJcJTU` の **「FY27｜個人予実」タブ（gid=824663141）**。

1. gviz CSV を取得（Claude in Chrome の新規タブで開くと `~/Downloads/data*.csv` にDL）:
   `https://docs.google.com/spreadsheets/d/1enM8QTz45P1NKSjX4pVqTIXOhB-S8qKnjr4sHKJcJTU/gviz/tq?tqx=out:csv&gid=824663141`
2. CSV から「岩野」ブロック（各重要指標: 新規開業室数 / 契約室数 / 口頭合意室数 / リード室数 / 案件獲得数）の
   `目標` `実績` `差分` `達成率` `月日数進捗差分率` の**月次12列（当年度8月〜翌7月）**を抽出し、
   `dashboard/kpi_raw.json` を更新:
   ```json
   {"months":["2026/08",…,"2027/07"],
    "blocks":{"新規開業室数":{"目標":[…12個],"実績":[…],"差分":[…],"達成率":[…],"月日数進捗差分率":[…]}, …}}
   ```
   **抽出は `python3 dashboard/extract_kpi.py <個人予実CSV>` を使う**（範囲指定で岩野ブロックを特定。`RANGES` がズレたらそこを直す）。
   ロジック: 指標ごとの行範囲で最初の `col index 3 == "岩野"` 行が岩野ブロック先頭、直後5行が 目標/実績/差分/達成率/月日数進捗差分率。月次列 = "FY27｜予実管理" 行で `2026/…` `2027/…` に一致する列の先頭12個。
   ※ 「col0==指標名で上方探索」は 案件獲得数 で誤検知する（末尾に空の岩野行がある）。範囲指定で回避。

## ④ 案件管理（岩野）

スプレッドシート `1N1tic41kZF-LwNNBhnKt29hjLxHlLciTqAl77Wvoj24` の **「02｜案件管理」タブ**
（※ユーザー共有URLの gid=2043602521 は別タブ「通年｜予実DB」なので注意。シート名で取得する）。

1. gviz CSV を取得（`~/Downloads/` にDLされる。`案件管理_YYYYMMDD.csv` にリネーム推奨）:
   `https://docs.google.com/spreadsheets/d/1N1tic41kZF-LwNNBhnKt29hjLxHlLciTqAl77Wvoj24/gviz/tq?tqx=out:csv&sheet=02%EF%BD%9C%E6%A1%88%E4%BB%B6%E7%AE%A1%E7%90%86`
2. `build.py --cases <そのCSV>` で渡す（`J列=案件推進者` が「岩野」の行を採用）。
   使う列: 案件進捗 / 案件属性 / 顧客属性 / 顧客名 / 契約社名 / **案件名（I列）** / 確度 / 現況区分 / 取得区分 / タイプ / エリア / 建物名称 / **AA列（index 26・ヘッダ無しの日付＝ステータス更新日）**。
   **アセットタイプ（ホテル/レジデンス）**は I列（案件名）の記載から判定（build.py の `asset_kind`）。タイプ列(AK)と一致する。
   **ホット案件の定義**: 確度が「D：担当者が提案を魅力的に感じている（賃料目線が目標に達している）」で始まり、かつ **AA列の日付が当月**（`--month YYYY-MM`）の案件。月間目標 10件。build.py が自動判定（`is_hot`）。

---

## ⑤ 組み立て & 再パブリッシュ

```bash
python3 dashboard/extract_kpi.py "$(ls -t ~/Downloads/data*.csv ~/Downloads/個人予実*.csv | head -1)"
python3 dashboard/build.py \
  --cases   "$(ls -t ~/Downloads/案件管理*.csv ~/Downloads/data*.csv | head -1)" \
  --month   2026-09     # ← 当月 YYYY-MM に更新（テンプレートの月表記・KPI既定月は build 時の --month に自動追従）
```
`dashboard/data.json` と `sales_dashboard.html` が再生成される。ローカルで簡単に表示確認したら、
**Artifact ツールで `url=https://claude.ai/code/artifact/e19c2c28-d5b6-4c9e-ab86-55b5b2ca007b` を指定して再パブリッシュ**（URLを変えない）。
`--cards` は省略で `~/Downloads/名刺出力*.csv` の最新を自動採用。

## 注意点

- 分類ロジック（会社名→6業態）は `dashboard/build.py` の `OVERRIDE` / `KW`。誤分類はここに会社名を足して直す。`その他` は非不動産業（銀行・ホテル・法律事務所・自治体等）を含み、多くて正常。
- Claude in Chrome が未接続なら、ユーザーに拡張機能のインストール/サインインを案内するか、ユーザー自身にCSVを `~/Downloads/` へ置いてもらう。
- gviz エクスポートは**ファイルダウンロード**として発生する（`~/Downloads/data.csv`, `data (1).csv` …）。実行前にユーザーへ一言伝える。
- 更新後、変更点（各件数の増減）を1〜2行でユーザーに要約する。

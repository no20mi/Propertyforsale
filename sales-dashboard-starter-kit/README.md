# セールスアクション台帳 — スターターキット

個人の営業アクション・成果を1画面で管理するダッシュボードです。元は岩野希美さん個人用に作られたものを、
**他の人が自分用にコピーしてセットアップできるよう汎用化**したキットです。

デモ（同梱のサンプルデータで生成したもの）: `sales_dashboard.html` をブラウザで直接開けば見られます。
サーバーもインストールも不要な、1ファイルの静的HTMLです。

## この中に何が入っているか

```
sales_dashboard.html   ← 完成品デモ（sample_data の架空データで生成済み。まず開いて動作を見る用）
dashboard/
  template.html        ← アプリ本体のHTML/CSS/JS（データは /*DATA*/ の場所に埋め込まれる）
  build.py             ← 4つの入力から data.json と sales_dashboard.html を生成するビルドスクリプト
  extract_kpi.py       ← 個人予実シートのCSVから自分のブロックを抜き出すスクリプト（要カスタマイズ）
  data.json            ← build.py の出力（今はデモ用のサンプルデータが入っている）
sample_data/           ← 動作確認用の架空データ一式（実在の企業ではありません）
REFERENCE_ORIGINAL_UPDATE_PLAYBOOK.md
                        ← 元の運用（岩野さん個人用）で実際に使っていた更新手順書。
                          Googleカレンダー／スプレッドシートの取得方法の実例として参考にしてください
                          （中のスプレッドシートIDやメールアドレスは元の持ち主のものなので、
                          自分のものに置き換えて読んでください）。
```

## アプリの4セクション

1. **クライアント属性** — 名刺データを一覧化し、会社名から業態を6分類（ファンド／AM／仲介／デベロッパー／総合不動産／不動産コンサルタント）して割合を表示
2. **営業アクション数** — カレンダーの訪問・来社・オンライン打合せ予定を月次集計し、毎月のKPI（アポ数・ホット案件数）を進捗バーで表示
3. **個人予実** — 予実管理シートの自分のブロックから重要指標を抽出し、当月の目標/実績/達成率と12か月推移を表示
4. **案件管理** — 案件管理シートから自分が担当する案件を抽出し、アセットタイプ・取得区分・進捗・確度・顧客業態などで集計＋一覧表示

## クイックスタート（サンプルデータで動作確認）

```bash
cd starter-kit
python3 dashboard/build.py \
  --cards sample_data/cards_sample.csv \
  --cases sample_data/cases_sample.csv
open sales_dashboard.html   # Macの場合。他OSはファイルをダブルクリック
```
`--meetings` / `--kpi` を省略すると `dashboard/meetings.json` / `dashboard/kpi_raw.json`（サンプルデータを仕込み済み）が使われます。
これで `sales_dashboard.html` が再生成され、そのままブラウザで開けます。

## 自分用にセットアップする手順

### ① `dashboard/build.py` の CONFIG を書き換える

ファイル冒頭の `CONFIG = {...}` ブロックがすべての個人設定です。

| キー | 説明 |
|---|---|
| `person` | 案件管理CSVの「案件推進者」列・個人予実シートの担当者名と**完全一致**させる文字列（例: 姓のみ） |
| `person_display` | サイドバーに表示するフルネーム |
| `calendar_email` | 集計対象のGoogleカレンダーのアカウント（表示用） |
| `exclude_company_name` | 集計から除外したい取引先名（不要なら `''` にすると除外機能自体がオフになる） |
| `exclude_company_regex` | 上記を顧客名列から判定する正規表現（表記ゆれ対策） |
| `hot_kakudo_prefix` | 「ホット案件」とみなす確度列の接頭辞（例: `D：`） |
| `apo_target` / `hot_target` | 毎月のKPI目標値 |

### ② 4つの入力データを用意する

| 入力 | 形式 | 用意の仕方 |
|---|---|---|
| 名刺CSV | UTF-8(BOM可)、ヘッダ `会社名,部署名,役職,氏名,郵便番号(1),住所(1)［全て］,TEL-1(1),FAX(1),Email(1),...` | 名刺管理ツールからエクスポート |
| 案件管理CSV | `案件ID,...,案件進捗,案件属性,顧客属性,顧客名,契約社名,案件名,案件推進者,案件獲得者,...,確度,...,現況区分,取得区分,...` の見出し行を含むCSV。**AA列（0始まりでindex26、見出し無し）に日付が入っている前提**（ステータス更新日） | Googleスプレッドシートの案件管理タブを gviz CSV エクスポート、または手動エクスポート |
| `dashboard/meetings.json` | `[{"type":"往訪"\|"来社"\|"meets","date":"YYYY-MM-DD","title":"件名","status":"承諾"\|"辞退"\|"出欠確認が必要"\|"","daito":true/false}]` | Googleカレンダーを見ながら手動で作成、または後述の方法で自動抽出 |
| `dashboard/kpi_raw.json` | `{"months":["YYYY/MM",...12個],"blocks":{"指標名":{"目標":[...12],"実績":[...12],"差分":[...12],"達成率":[...12],"月日数進捗差分率":[...12]}}}` | `dashboard/extract_kpi.py` で個人予実シートのCSVから抽出、または手で作成 |

`meetings.json` の `daito` は「集計対象から除外する予定かどうか」を1件ずつ人手（またはAI）で判定してセットするフラグです。
`exclude_company_name` が空でも `daito:true` にした予定は除外されます — CONFIGの exclude_company_name は主に画面上の文言表示用です。

> `dashboard/meetings.json` と `dashboard/kpi_raw.json` には最初からサンプルデータが入っています（動作確認用）。
> 自分のデータに差し替える場合は、このファイルを上書きするか `--meetings` / `--kpi` で別ファイルを指定してください。

### ③ 案件管理CSVのAA列について

案件管理シートに「ステータス更新日」のような、見出しの無い日付列がある場合、`build.py` は**列の位置（0始まりで26番目=AA列）**でそれを読みます。
自分のシートで位置が違う場合は `dashboard/build.py` の `iAA=26` を実際の列位置に直してください。この列がなければ「ホット案件」機能は使えないので、`hot_target` を `0` にするか、`is_hot` の判定式を自分の運用に合わせて書き換えてください。

### ④ 個人予実データの抽出をカスタマイズする

`dashboard/extract_kpi.py` は元のスプレッドシートのレイアウト（縦に「指標→担当者ごとのブロック→目標/実績/差分/達成率/月日数進捗差分率の5行」が並ぶ形式）に合わせた実装です。
シートが違えば **`RANGES`（指標ごとの行範囲）を自分のシートに合わせて調整する必要があります**。手順:

1. スプレッドシートの個人予実タブを `File > Share > Publish to web` などでCSV化、または `.../gviz/tq?tqx=out:csv&gid=<タブのgid>` 形式のURLでエクスポート
2. CSVを開き、自分の名前が入っている行（列D＝index3）を指標ごとに探し、だいたいの行範囲を `RANGES` に書く
3. `python3 dashboard/extract_kpi.py <CSVファイル>` を実行し、エラーが出たら `RANGES` を調整

レイアウトが大きく異なる場合は、この抽出ロジックにこだわらず、**`dashboard/kpi_raw.json` を上のスキーマ通りに直接手書き/生成しても構いません**（build.pyはこのJSONを読むだけです）。

### ⑤ カレンダーからの自動抽出（Claude Codeを使う場合）

`REFERENCE_ORIGINAL_UPDATE_PLAYBOOK.md` に、Claude Code + Claude in Chrome（ログイン済みブラウザ）を使って
「Googleカレンダーの検索ビューで（往訪）（来社）（meets）を検索 → 自分のカレンダーの予定だけ抽出 → meetings.json に整形」
という手順の実例が載っています。スプレッドシートのIDやメールアドレスは元の持ち主のものなので、自分のものに読み替えてください。

自動化せず、カレンダーを見ながら手でJSONを書いても問題ありません。

### ⑥ ビルド＆公開

```bash
python3 dashboard/build.py \
  --cards   自分の名刺CSVパス \
  --cases   自分の案件管理CSVパス \
  --month   2026-09   # 省略時は実行時点の年月
```
`dashboard/data.json` と `sales_dashboard.html` が再生成されます。`sales_dashboard.html` は完全に自己完結した1ファイルなので、

- ブラウザでそのまま開く
- 社内共有ドライブに置く
- Claude Code の Artifact 機能などでWeb公開する

好きな方法で配布・閲覧できます。データを更新したら同じコマンドを再実行して配布し直すだけです。

## カスタマイズのヒント

- **業態6分類のロジック**（`dashboard/build.py` の `OVERRIDE` / `KW`）はキーワードベースの推定です。誤分類があれば `OVERRIDE` に会社名を追記して直してください。分類が不要なら `classify()` を単純化しても構いません。
- **画面のテキスト・色・レイアウト**は `dashboard/template.html` のCSS変数（`:root{...}`）とHTML/JSを直接編集してください。ライト/ダーク両対応のCSS変数構成になっています。
- サンプルデータはすべて架空の会社名・人名です（実在の企業とは関係ありません）。

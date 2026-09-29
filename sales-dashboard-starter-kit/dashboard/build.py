#!/usr/bin/env python3
"""セールスアクション台帳ダッシュボードのデータ生成 + HTML組み立て。

これは「岩野希美さん個人用」の実装を汎用テンプレート化したスターターキットです。
自分用にセットアップするには、まず下の CONFIG を書き換えてください。

入力（すべて dashboard/ からの相対 or 絶対パス。--cards などで上書き可）:
  - 名刺CSV        : ~/Downloads/名刺出力*.csv（最新）
  - 案件管理CSV    : ~/Downloads/案件管理*.csv or data*.csv（gvizエクスポート）
  - 個人予実CSV    : ~/Downloads/個人予実*.csv or data*.csv（gvizエクスポート。--kpi 経由でも可）
  - カレンダー明細 : dashboard/meetings.json（手動更新: [{type,date,title,status,daito}]）
  - kpi_raw.json   : dashboard/kpi_raw.json（個人予実シートの担当者ブロック抽出結果。extract_kpi.py で生成）

出力:
  - dashboard/data.json
  - sales_dashboard.html（template.html にデータを埋め込み）

使い方: python3 dashboard/build.py
詳しいセットアップ手順は README.md を参照。
"""
import csv, json, collections, sys, glob, os, argparse, datetime

ROOT=os.path.dirname(os.path.abspath(__file__))
PROJ=os.path.dirname(ROOT)
DL=os.path.expanduser('~/Downloads')

# ============================================================
#  CONFIG — ここを自分用に書き換える
# ============================================================
CONFIG={
  # 案件管理CSVの「案件推進者」列・個人予実シートの担当者名と完全一致させる文字列
  'person': '岩野',
  # サイドバーに表示するフルネーム
  'person_display': '岩野 希美',
  # Googleカレンダーの対象アカウント（表示用ラベル）
  'calendar_email': 'nozomi.iwano@unito.me',
  # 集計から除外したい取引先名（不要なら '' にする＝除外機能そのものをオフ）
  'exclude_company_name': '大東建託株式会社',
  # ↑を顧客名列から判定する正規表現（表記ゆれを吸収。空文字なら exclude_company_name の完全一致のみ）
  'exclude_company_regex': '大[東都]建託',
  # 「ホット案件」の判定: 確度列がこの文字列で始まり、かつ AA列（更新日）が当月の案件
  'hot_kakudo_prefix': 'D：',
  'hot_definition_label': '確度が指定プレフィックスで始まり、かつ更新日（AA列）が当月の案件',
  # 毎月のKPI目標
  'apo_target': 30,
  'apo_label': 'アポ',
  'hot_target': 10,
  'hot_label': 'ホット案件',
}
if CONFIG['exclude_company_name']:
    CONFIG['apo_label']=f"アポ（{CONFIG['exclude_company_name']}以外）"
CONFIG['hot_label']=f"ホット案件（確度{CONFIG['hot_kakudo_prefix'].rstrip('：:')}・当月）"
# ============================================================

def newest(*patterns):
    hits=[]
    for p in patterns:
        hits+=glob.glob(p)
    if not hits: return None
    return max(hits, key=os.path.getmtime)

ap=argparse.ArgumentParser()
ap.add_argument('--cards', default=newest(f'{DL}/名刺出力*.csv'))
ap.add_argument('--cases', default=newest(f'{DL}/案件管理*.csv', f'{DL}/02｜案件管理*.csv'))
ap.add_argument('--yojitsu', default=newest(f'{DL}/個人予実*.csv', f'{DL}/FY27｜個人予実*.csv'))
ap.add_argument('--meetings', default=f'{ROOT}/meetings.json')
ap.add_argument('--kpi', default=f'{ROOT}/kpi_raw.json')
ap.add_argument('--month', default=datetime.date.today().strftime('%Y-%m'), help='当月 YYYY-MM')
a=ap.parse_args()
print('cards   :', a.cards)
print('cases   :', a.cases)
print('yojitsu :', a.yojitsu, '(未指定なら kpi_raw.json を使用)')
print('meetings:', a.meetings)

CATS=['ファンド','AM','仲介','デベロッパー','総合不動産','不動産コンサルタント','その他']

# 会社名 -> 業態 の分類（優先: 明示OVERRIDE -> キーワード）
OVERRIDE={
 '大東建託':'デベロッパー','大和ハウス':'デベロッパー','積水ハウス':'デベロッパー',
 '伊藤忠都市開発':'総合不動産','三菱地所':'総合不動産','三井不動産':'総合不動産','住友不動産':'総合不動産',
 '東急不動産':'総合不動産','野村不動産ソリューションズ':'仲介','野村不動産':'総合不動産','東京建物':'総合不動産',
 'ヒューリック':'総合不動産','日鉄興和不動産':'総合不動産','大成有楽不動産':'総合不動産','小田急不動産':'総合不動産',
 '東武不動産':'総合不動産','サンケイビル':'総合不動産','オリックス不動産':'総合不動産','安田不動産':'総合不動産',
 '福岡地所':'総合不動産','地主株式会社':'総合不動産','西日本鉄道':'総合不動産','京成電鉄':'総合不動産',
 '京急開発':'総合不動産','西日本新聞ビル':'総合不動産','トーセイ':'総合不動産','スターツ':'総合不動産',
 'セゾンリアルティ':'総合不動産',
 '東急リバブル':'仲介','三菱地所リアルエステートサービス':'仲介','三菱地所リアルエステート':'仲介','三幸':'仲介',
 'ジョーンズラングラサール':'仲介','ジョーンズ ラング ラサール':'仲介','あなぶきレジデンシャル流通':'仲介',
 '信和不動産販売':'仲介','R&Yエステート':'仲介','北辰不動産':'仲介','一戸不動産':'仲介','プロックス不動産':'仲介',
 'Post Lintel Realty':'仲介','J.P.RETURNS':'仲介','リバイブル':'仲介','レジデンシャル流通':'仲介',
 '丸紅リートアドバイザーズ':'AM','オリックス・アセットマネジメント':'AM','ラサール不動産投資顧問':'AM',
 '長谷工':'AM','リサ投資顧問':'AM','ヒューリック不動産投資顧問':'AM','イデラキャピタルマネジメント':'AM',
 'イデラ キャピタルマネジメント':'AM','SREアセットマネジメント':'AM','リストアセットマネジメント':'AM',
 '地主アセットマネジメント':'AM','ムゲンアセットマネジメント':'AM','キンカ・アセットマネジメント':'AM',
 'フィンテックアセットマネジメント':'AM','EGWアセットマネジメント':'AM','三幸アセットマネジメント':'AM',
 'スターアジア・マネジメント':'AM','SBIプライベートリートアドバイザーズ':'AM','大東建託インベストメント・マネジメント':'AM',
 '대東建託アセットソリューション':'AM','大東建託アセットソリューション':'AM','大東建託アセット':'AM',
 'Post Lintel Investment Management':'AM','ポスト・リンテルインベストメントマネジメント':'AM',
 'シマダアセットパートナーズ':'AM','MGアセット':'AM','アセットマネジメントホールディングス':'AM','KJRマネジメント':'AM',
 'サムライ・キャピタル':'ファンド','ユニ・アジアキャピタルジャパン':'ファンド','リサ・パートナーズ':'ファンド',
 '栄泰投資控股':'ファンド','キャピタルジェネレーション':'ファンド','フォートレス・インベストメント':'ファンド',
 'プロプリアム・キャピタル・パートナーズ':'ファンド','スリーアイズキャピタル':'ファンド','インテグラル・リアルエステート':'ファンド',
 'rh investment':'ファンド','RAFT':'ファンド','スターアジア':'ファンド','NI Capital':'ファンド','NI capital':'ファンド',
 'Garabato Group':'ファンド','ポスト・リンテル株式会社':'ファンド',
 'マスダアンドアソシエイツ':'不動産コンサルタント','株式化者マスダアンドアソシエイツ':'不動産コンサルタント',
 'クロスパス・アドバイザーズ':'不動産コンサルタント','ロータスアドバイザリー':'不動産コンサルタント',
 '青山リアルティー・アドバイザーズ':'不動産コンサルタント','オーバル・パートナーズ':'不動産コンサルタント',
 '梛パートナーズ':'不動産コンサルタント','アドバンス・シティ・プランニング':'不動産コンサルタント',
 'エービーコンサルティング':'不動産コンサルタント','イーグルコンサルティング':'不動産コンサルタント',
 'KYCコンサルティング':'不動産コンサルタント','三友システムアプレイザル':'不動産コンサルタント',
 '銀座プランニング':'不動産コンサルタント','阿波総合企画':'不動産コンサルタント','ASK PLANNING':'不動産コンサルタント',
 'デザインアーク':'デベロッパー','ムゲンエステート':'デベロッパー','プロパスト':'デベロッパー','ビーロット':'デベロッパー',
 'レーサム':'デベロッパー','コスモスイニシア':'デベロッパー','サムティ':'デベロッパー','明和地所':'デベロッパー',
 '穴吹興産':'デベロッパー','開拓地所':'デベロッパー','アスコット':'デベロッパー','マリモ':'デベロッパー',
 'タカラレーベン':'デベロッパー','リビングコーポレーション':'デベロッパー','ケイアイスター不動産':'デベロッパー',
 'セレコーポレーション':'デベロッパー','生和コーポレーション':'デベロッパー','サンヨーホームズ':'デベロッパー',
 '大和財託':'デベロッパー','リブマックス':'デベロッパー','東通建物':'デベロッパー','相互住宅':'デベロッパー',
 '東京ミライエステート':'デベロッパー','ジェイレックス':'デベロッパー','コロンビアワークス':'デベロッパー',
 'ネクストラスト':'デベロッパー','ネクストトラスト':'デベロッパー','RETRUS':'デベロッパー','レイシャス':'デベロッパー',
 'アイディ株式会社':'デベロッパー','あなぶき':'デベロッパー',
}
KW=[
 ('AM',['アセットマネジメント','アセット・マネジメント','投資顧問','リートアドバイザーズ','リート・マネジメント',
        'リートマネジメント','インベストメント・マネジメント','インベストメントマネジメント','investment management',
        'asset management','アセットソリューション','リート・アドバイザーズ']),
 ('ファンド',['キャピタル','capital','パートナーズ','partners','ファンド',' fund','投資控股','エクイティ','equity',
        'インベストメント','investment']),
 ('仲介',['リバブル','リハウス','不動産販売','ソリューションズ','リアルエステートサービス','エステートサービス',
        'jll','cbre','流通','仲介']),
 ('総合不動産',['都市開発','不動産株式会社','地所','鉄道','電鉄','ビルディング','ビル株式会社']),
 ('デベロッパー',['建設','工務店','ハウス','ホームズ','興産','ディベロップ','分譲','レジデンシャル','コーポレーション','建物']),
 ('不動産コンサルタント',['コンサルティング','コンサル','アドバイザリー','アドバイザーズ','アソシエイツ','総合企画',
        'プランニング','総研','アプレイザル']),
]
def classify(name):
    if not name: return 'その他'
    for k,c in OVERRIDE.items():
        if k in name: return c
    low=name.lower()
    for c,kws in KW:
        if any(kw in name or kw in low for kw in kws): return c
    return 'その他'

PREFS=['北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県','茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県','新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県','静岡県','愛知県','三重県','滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県','鳥取県','島根県','岡山県','広島県','山口県','徳島県','香川県','愛媛県','高知県','福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県']
def pref(a):
    for p in PREFS:
        if a.startswith(p): return p
    return '不明'

# ---------- business cards ----------
if not a.cards or not os.path.exists(a.cards):
    sys.exit('名刺CSVが見つかりません。--cards で指定してください。')
bc=list(csv.DictReader(open(a.cards,encoding='utf-8-sig')))
def g(r,*keys):
    for k in keys:
        if k in r and r[k] is not None: return r[k].strip()
    return ''
cards=[]
for r in bc:
    co=g(r,'会社名')
    cards.append({'company':co,'dept':g(r,'部署名'),'title':g(r,'役職'),'name':g(r,'氏名'),
      'zip':g(r,'郵便番号(1)','郵便番号'),'addr':g(r,'住所(1)［全て］','住所(1)','住所'),
      'tel':g(r,'TEL-1(1)','TEL'),'fax':g(r,'FAX(1)','FAX'),'email':g(r,'Email(1)','Email'),
      'attr':classify(co)})
comp=collections.Counter(c['company'] for c in cards if c['company'])
prefc=collections.Counter(pref(c['addr']) for c in cards)
compAttr={co:classify(co) for co in comp}
cardAttrByCard=collections.Counter(c['attr'] for c in cards)
cardAttrByCompany=collections.Counter(compAttr.values())

# ---------- cases ----------
if not a.cases or not os.path.exists(a.cases):
    sys.exit('案件管理CSVが見つかりません。--cases で指定してください（02｜案件管理タブのgvizエクスポート）。')
rows=list(csv.reader(open(a.cases,encoding='utf-8')))
# ヘッダ行を探す（"案件ID" を含む行）
hi=next((i for i,r in enumerate(rows) if '案件ID' in r), 1)
H=rows[hi]
idx=lambda name: H.index(name) if name in H else None
iP=idx('案件進捗'); iAttr=idx('案件属性'); iCust5=idx('顧客属性'); iCustN=idx('顧客名')
iContr=idx('契約社名'); iName=idx('案件名'); iDriver=idx('案件推進者'); iGetter=idx('案件獲得者')
iKak=idx('確度'); iGen=idx('現況区分'); iAcq=idx('取得区分'); iType=idx('タイプ'); iArea=idx('エリア'); iBld=idx('建物名称')
iAA=26  # AA列（ヘッダ無し・日付。ステータス更新日）。gvizエクスポートは列順を保持するので AA=index 26。
def cell(r,i): return r[i].strip() if (i is not None and i<len(r)) else ''
def norm_month(s):
    # "2026/08/07" / "2026-08-07" / "2026/8/7" -> "2026-08"
    import re
    m=re.match(r'(\d{4})[/-](\d{1,2})',s or '')
    return f'{m.group(1)}-{int(m.group(2)):02d}' if m else ''
def asset_kind(name):
    # I列（案件名）の記載からアセットタイプを判定
    nm=name or ''
    tags=[]
    if 'ホテル' in nm: tags.append('ホテル')
    if 'レジデンス' in nm or 'レジ' in nm: tags.append('レジデンス')
    if 'ヴィラ' in nm: tags.append('ヴィラ')
    return '／'.join(tags) if tags else '（判別不可）'
cases=[]
for r in rows[hi+1:]:
    if cell(r,iDriver)!=CONFIG['person']: continue
    cust=cell(r,iCustN)
    aa=cell(r,iAA)
    kak=cell(r,iKak)
    nm=cell(r,iName)
    is_hot = kak.startswith(CONFIG['hot_kakudo_prefix']) and norm_month(aa)==a.month
    cases.append({'id':cell(r,idx('案件ID')),'progress':cell(r,iP),'attr':cell(r,iAttr),'custAttr':cell(r,iCust5),
      'customer':cust,'contract':cell(r,iContr),'name':nm,'getter':cell(r,iGetter),
      'kakudo':kak,'genkyo':cell(r,iGen),'acq':cell(r,iAcq),'aa':aa,'hot':is_hot,
      'type':cell(r,iType),'kind':asset_kind(nm),
      'area':cell(r,iArea),'building':cell(r,iBld),'clientAttr':classify(cust)})
hot=[c for c in cases if c['hot']]
caseKind=collections.Counter(c['kind'] for c in cases)
caseClientAttr=collections.Counter(c['clientAttr'] for c in cases)
caseAcq=collections.Counter(c['acq'] or '（未設定）' for c in cases)
caseGenkyo=collections.Counter(c['genkyo'] or '（未設定）' for c in cases)

# ---------- meetings ----------
if not os.path.exists(a.meetings):
    sys.exit(f'{a.meetings} が見つかりません。SKILL.md の手順②でカレンダー明細を作成してください。')
meetings=json.load(open(a.meetings))
counted=[m for m in meetings if not m.get('daito')]

# ---------- KPI ----------
kpi=json.load(open(a.kpi))

out={
 'generated':datetime.date.today().isoformat(),
 'cards':cards,
 'cardCompanyCounts':comp.most_common(),
 'cardPrefCounts':prefc.most_common(),
 'cardAttrByCard':cardAttrByCard.most_common(),
 'cardAttrByCompany':cardAttrByCompany.most_common(),
 'attrCats':CATS,
 'kpi':kpi,
 'cases':cases,
 'caseKindCounts':caseKind.most_common(),
 'caseClientAttr':caseClientAttr.most_common(),
 'caseAcqCounts':caseAcq.most_common(),
 'caseGenkyoCounts':caseGenkyo.most_common(),
 'meetings':meetings,
 'meetingMonth':a.month,
 'monthlyKPI':{
   'apo':{'actual':len(counted),'target':CONFIG['apo_target'],'label':CONFIG['apo_label']},
   'hot':{'actual':len(hot),'target':CONFIG['hot_target'],'label':CONFIG['hot_label']},
 },
 'hotCases':[{'customer':c['customer'],'name':c['name'],'area':c['area'],'aa':c['aa'],'clientAttr':c['clientAttr']} for c in hot],
 'config':{
   'person':CONFIG['person'],'personDisplay':CONFIG['person_display'],
   'calendarEmail':CONFIG['calendar_email'],
   'excludeCompanyName':CONFIG['exclude_company_name'],
   'excludeCompanyRegex':CONFIG['exclude_company_regex'],
   'hotDef':CONFIG['hot_definition_label'],
 },
 'cardsSrcFile':os.path.basename(a.cards),
 'kpiSrcLabel':os.path.basename(a.yojitsu) if a.yojitsu else '個人予実シート',
 'casesSrcLabel':os.path.basename(a.cases),
}
json.dump(out,open(f'{ROOT}/data.json','w'),ensure_ascii=False)

tpl=open(f'{ROOT}/template.html').read()
data=json.dumps(out,ensure_ascii=False).replace('</','<\\/')
open(f'{PROJ}/sales_dashboard.html','w').write(tpl.replace('/*DATA*/',data))

print(f'\nOK  名刺 {len(cards)}件 / 案件 {len(cases)}件 / ホット {len(hot)}件 / アポ計上 {len(counted)}件')
print(f'    -> {PROJ}/sales_dashboard.html')
print('    次: このファイルをブラウザで開くか、Artifact機能等で公開してください。')

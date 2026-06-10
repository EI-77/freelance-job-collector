# Freelance Job Collector

クラウドワークスの案件情報を収集し，Excelレポートとして出力するPythonツールです．

複数の検索キーワードを指定し，案件タイトル，報酬，応募人数，締切，案件URLを取得できます．

取得した案件はURLを基準に重複除外され，過去の取得履歴をもとに新着案件も判定できます．

また，案件一覧だけでなく，キーワード別の集計，高単価案件，応募人数が少ない案件もExcelシートとして出力できます．

副業案件の検索，新着案件の確認，案件市場の調査，報酬相場の確認などに利用できます．


---

## 主な機能

* クラウドワークス案件の収集
* 複数キーワード検索
* 重複案件の自動除外
* 最低報酬によるフィルタリング
* 除外キーワードによるフィルタリング
* 新着案件の自動判定
* Excelレポート出力
* キーワード別集計
* 高単価案件の抽出
* 応募人数が少ない案件の抽出
* Excelの列幅自動調整
* Excel見出し行の装飾
* Excelフィルター設定

---

## 使用技術

* Python
* Selenium
* BeautifulSoup
* pandas
* xlsxwriter

---

## 実行方法

### 1. リポジトリを取得

```bash
git clone <repository_url>
```

### 2. ディレクトリへ移動

```bash
cd freelance-job-collector
```

### 3. 必要ライブラリをインストール

```bash
pip install -r requirements.txt
```

### 4. キーワードを設定

`keywords.txt` に検索キーワードを1行ずつ入力します．

例

```text
Python
スクレイピング
データ収集
Excel 自動化
```

### 5. プログラムを実行

```bash
python freelance_job_collector.py
```

または

```bash
py freelance_job_collector.py
```

---

## 設定

動作設定は `config.json` で変更できます．

### default設定

```json
{
    "max_pages_per_keyword": 1,
    "min_price": 0,
    "exclude_words": [
        "電話",
        "営業",
        "出品"
    ]
}
```

| 項目                    | 内容                       |
| --------------------- | ------------------------ |
| max_pages_per_keyword | キーワードごとに取得するページ数 |
| min_price             | 出力対象にする最低報酬         |
| exclude_words         | タイトルに含まれていたら除外する語句 |

### ユーザー設定

default設定から変更する場合，`config.json` に任意の設定を記載し，`freelance_job_collector.py` と同じ階層に配置してください．

`config.json` が存在しない場合は，初回実行時にサンプル設定ファイルが自動作成されます．

---

## 出力ファイル

実行後，`output` フォルダにExcelファイルが出力されます．

### all_jobs

今回取得した全案件を出力します．

### new_jobs

前回実行時までに取得していなかった新着案件のみを出力します．

新着案件がない場合，`new_jobs` のExcelファイルは作成されません．

---

## Excelシート

出力されるExcelファイルには，以下のシートが含まれます．

### jobs

取得した案件一覧を出力します．

| Column       | Description |
| ------------ | ----------- |
| is_new       | 新着案件かどうか |
| keyword      | 検索キーワード |
| title        | 案件タイトル |
| price        | 報酬額 |
| deadline     | 締切 |
| applicants   | 応募人数 |
| url          | 案件URL |
| collected_at | 取得日時 |

### summary

取得結果の概要を出力します．

主な内容は以下です．

* 総案件数
* 新着案件数
* 平均報酬
* 最高報酬
* キーワード別案件数
* キーワード別平均報酬
* キーワード別最高報酬

### high_price_jobs

報酬額が高い案件を上位順に出力します．

案件一覧全体から高単価案件を探す手間を減らせます．

### low_applicants_jobs

応募人数が取得できている案件のうち，応募人数が少ない案件を上位順に出力します．

応募人数が少ない案件は競争が少ない可能性があります．ただし，案件の条件や報酬も合わせて確認してください．

---

## 活用方法

* 副業案件の定期確認
* 新着案件の監視
* 案件市場の調査
* 技術トレンドの調査
* 報酬相場の確認
* 高単価案件の確認
* 応募競争が少ない案件の確認
* ポートフォリオ作成のための市場分析

---

## 注意事項

* 取得済み案件は `data/seen_jobs.json` に保存されます．
* 同じ案件が複数キーワードで見つかった場合，URLを基準に重複除外されます．
* Google Chrome が必要です．
* クラウドワークスの仕様変更により動作しなくなる可能性があります．
* 詳細ページまでは巡回しないため，検索結果一覧に表示されない情報は取得できません．
* 出力ファイルは `output` フォルダに保存されます．

---

# English

## Overview

Freelance Job Collector is a Python tool that collects job listings from CrowdWorks and exports them to Excel reports.

The tool supports multiple keyword searches, duplicate removal, filtering, new job detection, and Excel-based job analysis.

It is useful for freelance job hunting, market research, and rate analysis.

## Features

* CrowdWorks job collection
* Multiple keyword search
* Automatic duplicate removal
* Job filtering
* New job detection
* Excel report export
* Keyword-based summary
* High-price job extraction
* Low-applicant job extraction
* Auto-adjusted Excel column width
* Excel header formatting and filters

## Output Files

* all_jobs
* new_jobs

## Excel Sheets

* jobs
* summary
* high_price_jobs
* low_applicants_jobs

## Use Cases

* Freelance job hunting
* New job monitoring
* Market research
* Rate analysis
* Technology trend research
* Portfolio planning

## Limitations

* Job detail pages are not visited
* Google Chrome is required
* The tool may stop working if CrowdWorks changes its page structure

## Requirements

```text
selenium
beautifulsoup4
pandas
xlsxwriter
```

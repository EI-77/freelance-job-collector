import json
import os
import re
import time
from datetime import datetime
from urllib.parse import quote, urljoin

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


BASE_URL = "https://crowdworks.jp"
SEARCH_URL = "https://crowdworks.jp/public/jobs/search"
KEYWORDS_FILE = "keywords.txt"
CONFIG_FILE = "config.json"
DATA_DIR = "data"
OUTPUT_DIR = "output"
SEEN_JOBS_FILE = os.path.join(DATA_DIR, "seen_jobs.json")

DEFAULT_CONFIG = {
    "max_pages_per_keyword": 1,
    "min_price": 0,
    "exclude_words": [
        "電話",
        "営業",
        "出品",
    ]
}

JOB_DETAIL_URL_PATTERN = re.compile(r"^/public/jobs/\d+$")


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1000")
    options.add_argument("--lang=ja-JP")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)

    return driver


def load_keywords():
    keywords = []
    seen_keywords = set()

    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            keyword = line.strip()

            if keyword == "":
                continue

            if keyword in seen_keywords:
                continue

            keywords.append(keyword)
            seen_keywords.add(keyword)

    return keywords


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value

    return config


def load_seen_jobs():
    if not os.path.exists(SEEN_JOBS_FILE):
        return {}

    with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen_jobs(seen_jobs):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_jobs, f, ensure_ascii=False, indent=2)


def make_search_url(keyword, page):
    encoded_keyword = quote(keyword)

    url = (
        f"{SEARCH_URL}"
        f"?search%5Bkeywords%5D={encoded_keyword}"
        f"&hide_expired=true"
        f"&page={page}"
    )

    return url


def get_soup(driver, url):
    driver.get(url)
    time.sleep(5)

    html = driver.page_source

    return BeautifulSoup(html, "html.parser")


def clean_text(text):
    return " ".join(text.split())


def normalize_url(url):
    return url.split("?")[0].rstrip("/")


def is_job_detail_url(href):
    if href is None:
        return False

    path = normalize_url(href)

    return JOB_DETAIL_URL_PATTERN.match(path) is not None


def extract_price(text):
    text = text.replace("税込", "")
    text = text.replace("税抜", "")

    patterns = [
        r"固定報酬制\s*([\d,]+)\s*円\s*[〜~～-]\s*([\d,]+)\s*円",
        r"固定報酬制\s*([\d,]+)\s*円",
        r"時間単価制\s*([\d,]+)\s*円",
        r"予算\s*([\d,]+)\s*円\s*[〜~～-]\s*([\d,]+)\s*円",
        r"予算\s*([\d,]+)\s*円",
        r"([\d,]+)\s*円\s*[〜~～-]\s*([\d,]+)\s*円",
        r"([\d,]+)\s*円"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            price_text = match.group(match.lastindex)
            return int(price_text.replace(",", ""))

    return 0


def extract_deadline(text):
    patterns = [
        r"あと\d+日",
        r"残り\d+日",
        r"\d+月\d+日"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(0)

    return ""


def extract_applicants(text):
    patterns = [
        r"応募した人\s*(\d+)\s*人",
        r"応募人数\s*(\d+)\s*人",
        r"応募数\s*(\d+)\s*人",
        r"応募\s*(\d+)\s*人",
        r"(\d+)\s*人が応募"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

    return None


def find_job_links(soup):
    links = soup.find_all("a", href=True)
    job_links = []
    seen_urls = set()

    for link in links:
        href = link.get("href")

        if not is_job_detail_url(href):
            continue

        title = clean_text(link.get_text())

        if title == "":
            continue

        if title == "この仕事に似た仕事を依頼する":
            continue

        url = urljoin(BASE_URL, normalize_url(href))

        if url in seen_urls:
            continue

        job_links.append(link)
        seen_urls.add(url)

    return job_links


def get_text_segments(soup, job_links):
    page_text = clean_text(soup.get_text())
    segments = []
    cursor = 0

    titles = [
        clean_text(link.get_text())
        for link in job_links
    ]

    for i, title in enumerate(titles):
        start = page_text.find(title, cursor)

        if start == -1:
            segments.append("")
            continue

        if i + 1 < len(titles):
            next_title = titles[i + 1]
            end = page_text.find(next_title, start + len(title))

            if end == -1:
                end = len(page_text)
        else:
            end = len(page_text)

        segment = page_text[start:end]
        segments.append(segment)
        cursor = end

    return segments


def parse_job_link(link, keyword, block_text):
    title = clean_text(link.get_text())
    url = urljoin(BASE_URL, normalize_url(link.get("href")))

    price = extract_price(block_text)
    deadline = extract_deadline(block_text)
    applicants = extract_applicants(block_text)

    return {
        "keyword": keyword,
        "title": title,
        "price": price,
        "deadline": deadline,
        "applicants": applicants,
        "url": url
    }


def get_jobs_one_page(driver, keyword, page):
    url = make_search_url(keyword, page)

    try:
        soup = get_soup(driver, url)
    except Exception as e:
        print(f"Failed to fetch page: {url}")
        print(f"Error: {e}")
        return []

    job_links = find_job_links(soup)

    print(f"Job links found: {len(job_links)}")

    if len(job_links) == 0:
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(str(soup))

        print("No job links found. Saved debug.html.")
        return []

    segments = get_text_segments(soup, job_links)
    jobs = []

    for link, segment in zip(job_links, segments):
        job = parse_job_link(link, keyword, segment)
        jobs.append(job)

    return jobs


def collect_jobs(driver, keywords, config):
    all_jobs = []
    seen_urls = set()
    max_pages = config["max_pages_per_keyword"]

    for keyword in keywords:
        print(f"Searching keyword: {keyword}")

        for page in range(1, max_pages + 1):
            print(f"Page: {page}")

            jobs = get_jobs_one_page(driver, keyword, page)

            if len(jobs) == 0:
                break

            new_count = 0

            for job in jobs:
                if job["url"] in seen_urls:
                    continue

                all_jobs.append(job)
                seen_urls.add(job["url"])
                new_count += 1

            print(f"Added jobs: {new_count}")
            print(f"Duplicated jobs skipped: {len(jobs) - new_count}")

            if new_count == 0:
                break
            
            print()
            time.sleep(2)

    return all_jobs


def is_excluded(job, config):
    title = job["title"]

    for word in config["exclude_words"]:
        if word in title:
            return True

    if job["price"] < config["min_price"]:
        return True

    return False


def enrich_jobs(jobs, config, seen_jobs):
    enriched_jobs = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for job in jobs:
        if is_excluded(job, config):
            continue

        url = job["url"]
        is_new = url not in seen_jobs

        job["is_new"] = is_new
        job["collected_at"] = now

        enriched_jobs.append(job)

    return enriched_jobs


def update_seen_jobs(jobs, seen_jobs):
    for job in jobs:
        url = job["url"]

        if url not in seen_jobs:
            seen_jobs[url] = {
                "title": job["title"],
                "first_seen_at": job["collected_at"]
            }

    return seen_jobs


def make_output_path(prefix):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{prefix}_{timestamp}.xlsx"

    return os.path.join(OUTPUT_DIR, file_name)


def adjust_column_width(worksheet, df):
    for index, column in enumerate(df.columns):
        max_length = max(
            df[column].map(lambda value: len(str(value))).max(),
            len(column)
        )
        width = min(max_length + 2, 60)
        worksheet.set_column(index, index, width)


def format_worksheet(writer, worksheet, df):
    header_format = writer.book.add_format({
        "bold": True,
        "bg_color": "#D9EAF7",
        "border": 1
    })

    for col_num, column in enumerate(df.columns):
        worksheet.write(0, col_num, column, header_format)

    worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
    worksheet.freeze_panes(1, 0)


def make_summary_dfs(df):
    summary_df = pd.DataFrame([
        {
            "item": "total_jobs",
            "value": len(df)
        },
        {
            "item": "new_jobs",
            "value": int(df["is_new"].sum())
        },
        {
            "item": "average_price",
            "value": int(df["price"].mean())
        },
        {
            "item": "max_price",
            "value": int(df["price"].max())
        }
    ])

    keyword_summary_df = df.groupby("keyword").agg(
        job_count=("title", "count"),
        average_price=("price", "mean"),
        max_price=("price", "max")
    ).reset_index()

    keyword_summary_df["average_price"] = keyword_summary_df["average_price"].round(0).astype(int)

    return summary_df, keyword_summary_df


def format_header_row(writer, worksheet, df, startrow):
    header_format = writer.book.add_format({
        "bold": True,
        "bg_color": "#D9EAF7",
        "border": 1
    })

    for col_num, column in enumerate(df.columns):
        worksheet.write(startrow, col_num, column, header_format)


def save_excel(jobs, prefix):
    if len(jobs) == 0:
        print(f"No jobs to save: {prefix}")
        return

    output_path = make_output_path(prefix)

    df = pd.DataFrame(jobs)
    df = df[
        [
            "is_new",
            "keyword",
            "title",
            "price",
            "deadline",
            "applicants",
            "url",
            "collected_at"
        ]
    ]

    df = df.sort_values(
        ["keyword", "price"],
        ascending=[True, False]
    )

    df = df.fillna("")

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(
            writer,
            sheet_name="jobs",
            index=False
        )

        summary_df, keyword_summary_df = make_summary_dfs(df)

        high_price_df = df.sort_values(
            "price",
            ascending=False
        ).head(20)

        low_applicants_df = df[
            df["applicants"] != ""
        ].sort_values(
            "applicants",
            ascending=True
        ).head(20)

        summary_df.to_excel(
            writer,
            sheet_name="summary",
            index=False,
            startrow=0
        )

        keyword_summary_df.to_excel(
            writer,
            sheet_name="summary",
            index=False,
            startrow=len(summary_df) + 3
        )

        high_price_df.to_excel(
            writer,
            sheet_name="high_price_jobs",
            index=False
        )

        low_applicants_df.to_excel(
            writer,
            sheet_name="low_applicants_jobs",
            index=False
        )

        jobs_worksheet = writer.sheets["jobs"]
        summary_worksheet = writer.sheets["summary"]
        high_price_worksheet = writer.sheets["high_price_jobs"]
        low_applicants_worksheet = writer.sheets["low_applicants_jobs"]

        adjust_column_width(jobs_worksheet, df)
        adjust_column_width(summary_worksheet, summary_df)
        adjust_column_width(summary_worksheet, keyword_summary_df)
        adjust_column_width(high_price_worksheet, high_price_df)
        adjust_column_width(low_applicants_worksheet, low_applicants_df)

        format_worksheet(writer, jobs_worksheet, df)
        format_worksheet(writer, high_price_worksheet, high_price_df)
        format_worksheet(writer, low_applicants_worksheet, low_applicants_df)

        format_header_row(writer, summary_worksheet, summary_df, 0)
        format_header_row(writer, summary_worksheet, keyword_summary_df, len(summary_df) + 3)

    print(f"Excel saved: {output_path}")


def create_sample_files():
    if not os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
            f.write("Python\n")
            f.write("スクレイピング\n")
            f.write("データ収集\n")
            f.write("Excel 自動化\n")

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)


def main():
    create_sample_files()

    keywords = load_keywords()
    config = load_config()
    seen_jobs = load_seen_jobs()

    driver = create_driver()

    try:
        jobs = collect_jobs(driver, keywords, config)
    finally:
        driver.quit()

    jobs = enrich_jobs(jobs, config, seen_jobs)

    new_jobs = [
        job for job in jobs
        if job["is_new"]
    ]

    save_excel(jobs, "all_jobs")
    save_excel(new_jobs, "new_jobs")

    seen_jobs = update_seen_jobs(jobs, seen_jobs)
    save_seen_jobs(seen_jobs)

    print(f"Total jobs: {len(jobs)}")
    print(f"New jobs: {len(new_jobs)}")


if __name__ == "__main__":
    main()

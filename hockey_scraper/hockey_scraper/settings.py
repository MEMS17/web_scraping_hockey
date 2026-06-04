BOT_NAME = "hockey_scraper"

SPIDER_MODULES = ["hockey_scraper.spiders"]
NEWSPIDER_MODULE = "hockey_scraper.spiders"

ROBOTSTXT_OBEY = True

USER_AGENT = "hockey_scraper_student_project (+https://www.scrapethissite.com)"

DOWNLOAD_DELAY = 1

RANDOMIZE_DOWNLOAD_DELAY = True

CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

ITEM_PIPELINES = {
    "hockey_scraper.pipelines.SQLitePipeline": 300,
}

LOG_LEVEL = "INFO"

FEED_EXPORT_ENCODING = "utf-8"
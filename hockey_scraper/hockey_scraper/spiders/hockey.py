import scrapy


class HockeySpider(scrapy.Spider):
    name = "hockey"
    allowed_domains = ["www.scrapethissite.com"]
    start_urls = ["https://www.scrapethissite.com"]

    def parse(self, response):
        pass

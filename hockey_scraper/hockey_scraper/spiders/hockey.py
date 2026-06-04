import scrapy
from hockey_scraper.items import HockeyTeamItem


class HockeySpider(scrapy.Spider):
    name = "hockey"
    allowed_domains = ["www.scrapethissite.com"]
    start_urls = ["https://www.scrapethissite.com/pages/forms/"]

    def parse(self, response):
        """
        Parse une page de résultats et suit la pagination.
        """

        rows = response.css("tr.team")

        self.logger.info(f"{len(rows)} lignes trouvées sur {response.url}")

        for row in rows:
            item = HockeyTeamItem()

            item["team_name"] = self.clean_text(row.css("td.name::text").get())
            item["year"] = self.to_int(row.css("td.year::text").get())
            item["wins"] = self.to_int(row.css("td.wins::text").get())
            item["losses"] = self.to_int(row.css("td.losses::text").get())
            item["ot_losses"] = self.to_int(row.css("td.ot-losses::text").get())
            item["win_percentage"] = self.to_float(row.css("td.pct::text").get())
            item["goals_for"] = self.to_int(row.css("td.gf::text").get())
            item["goals_against"] = self.to_int(row.css("td.ga::text").get())
            item["goal_difference"] = self.to_int(row.css("td.diff::text").get())
            item["source_url"] = response.url

            yield item

        next_page = response.css("ul.pagination li a[aria-label='Next']::attr(href)").get()

        if not next_page:
            next_page = response.xpath("//a[contains(text(), '»')]/@href").get()

        if next_page:
            yield response.follow(next_page, callback=self.parse)

    @staticmethod
    def clean_text(value):
        if value is None:
            return None
        return value.strip()

    @staticmethod
    def to_int(value):
        if value is None:
            return None

        value = value.strip()

        if value == "":
            return None

        return int(value)

    @staticmethod
    def to_float(value):
        if value is None:
            return None

        value = value.strip()

        if value == "":
            return None

        return float(value)
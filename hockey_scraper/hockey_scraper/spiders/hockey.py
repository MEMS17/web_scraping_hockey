import scrapy
from urllib.parse import urlencode

from hockey_scraper.items import HockeyTeamItem


class HockeySpider(scrapy.Spider):
    name = "hockey"
    allowed_domains = ["www.scrapethissite.com"]

    base_url = "https://www.scrapethissite.com/pages/forms/"

    def __init__(self, q=None, *args, **kwargs):
        """
        q est un argument optionnel passé depuis le terminal.

        Exemple :
        scrapy crawl hockey -a q=Buffalo

        Dans ce cas, self.q vaut "Buffalo".
        """
        super().__init__(*args, **kwargs)
        self.q = q

    async def start(self):
        """
        Point d'entrée du spider pour Scrapy 2.13+ / 2.16.

        Si q est fourni :
        -> on reproduit le formulaire de recherche avec une URL paramétrée.

        Si q n'est pas fourni :
        -> on lance la collecte complète.
        """

        if self.q:
            params = {"q": self.q}
            url = f"{self.base_url}?{urlencode(params)}"

            self.logger.info("=" * 60)
            self.logger.info(f"Collecte filtrée demandée avec q = {self.q}")
            self.logger.info(f"URL appelée : {url}")
            self.logger.info("=" * 60)

        else:
            url = self.base_url

            self.logger.info("=" * 60)
            self.logger.info("Collecte complète sans filtre")
            self.logger.info(f"URL appelée : {url}")
            self.logger.info("=" * 60)

        yield scrapy.Request(
            url=url,
            callback=self.parse,
            dont_filter=True
        )

    def parse(self, response):
        """
        Parse une page de résultats :
        - extraction des lignes du tableau ;
        - création des items ;
        - suivi de la pagination.
        """

        self.logger.info(f"Réponse reçue : {response.url}")
        self.logger.info(f"Code HTTP : {response.status}")

        rows = response.css("tr.team")

        self.logger.info(f"Nombre de lignes trouvées sur cette page : {len(rows)}")

        if len(rows) == 0:
            self.logger.warning("Aucune ligne trouvée.")
            self.logger.warning("Sauvegarde de la réponse dans debug_response.html")

            with open("debug_response.html", "w", encoding="utf-8") as file:
                file.write(response.text)

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

        next_page = self.get_next_page(response)

        if next_page:
            self.logger.info(f"Page suivante trouvée : {next_page}")

            yield response.follow(
                next_page,
                callback=self.parse,
                dont_filter=True
            )
        else:
            self.logger.info("Aucune page suivante trouvée. Fin de la collecte.")

    def get_next_page(self, response):
        """
        Récupère le lien de pagination vers la page suivante.
        """

        next_page = response.css("ul.pagination li a[aria-label='Next']::attr(href)").get()

        if not next_page:
            next_page = response.xpath("//a[contains(text(), '»')]/@href").get()

        if not next_page:
            next_page = response.xpath("//a[contains(text(), 'Next')]/@href").get()

        return next_page

    @staticmethod
    def clean_text(value):
        """
        Nettoie les textes extraits du HTML.
        """

        if value is None:
            return None

        return value.strip()

    @staticmethod
    def to_int(value):
        """
        Convertit une valeur en entier.
        Si la valeur est vide, retourne None.
        """

        if value is None:
            return None

        value = value.strip()

        if value == "":
            return None

        return int(value)

    @staticmethod
    def to_float(value):
        """
        Convertit une valeur en nombre décimal.
        Si la valeur est vide, retourne None.
        """

        if value is None:
            return None

        value = value.strip()

        if value == "":
            return None

        return float(value)
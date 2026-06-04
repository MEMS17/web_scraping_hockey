import scrapy


class HockeyTeamItem(scrapy.Item):
    team_name = scrapy.Field()
    year = scrapy.Field()
    wins = scrapy.Field()
    losses = scrapy.Field()
    ot_losses = scrapy.Field()
    win_percentage = scrapy.Field()
    goals_for = scrapy.Field()
    goals_against = scrapy.Field()
    goal_difference = scrapy.Field()
    source_url = scrapy.Field()
import json
import os
import re
import sqlite3
from itemadapter import ItemAdapter


class SQLitePipeline:
    def open_spider(self, spider):
        self.conn = sqlite3.connect("hockey_teams.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS hockey_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                wins INTEGER,
                losses INTEGER,
                ot_losses INTEGER,
                win_percentage REAL,
                goals_for INTEGER,
                goals_against INTEGER,
                goal_difference INTEGER,
                source_url TEXT,
                UNIQUE(team_name, year)
            )
        """)

        self.conn.commit()

        self.json_file = None
        self.json_path = None
        self.filtered_items = []

        if getattr(spider, "q", None):
            os.makedirs("exports", exist_ok=True)

            safe_query = self.slugify(spider.q)
            self.json_path = f"exports/filter_{safe_query}.json"

            spider.logger.info(f"Export JSON du filtre prévu : {self.json_path}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        data = {
            "team_name": adapter.get("team_name"),
            "year": adapter.get("year"),
            "wins": adapter.get("wins"),
            "losses": adapter.get("losses"),
            "ot_losses": adapter.get("ot_losses"),
            "win_percentage": adapter.get("win_percentage"),
            "goals_for": adapter.get("goals_for"),
            "goals_against": adapter.get("goals_against"),
            "goal_difference": adapter.get("goal_difference"),
            "source_url": adapter.get("source_url"),
        }

        self.cursor.execute("""
            INSERT OR IGNORE INTO hockey_teams (
                team_name,
                year,
                wins,
                losses,
                ot_losses,
                win_percentage,
                goals_for,
                goals_against,
                goal_difference,
                source_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["team_name"],
            data["year"],
            data["wins"],
            data["losses"],
            data["ot_losses"],
            data["win_percentage"],
            data["goals_for"],
            data["goals_against"],
            data["goal_difference"],
            data["source_url"],
        ))

        self.conn.commit()

        if getattr(spider, "q", None):
            self.filtered_items.append(data)

        return item

    def close_spider(self, spider):
        if getattr(spider, "q", None) and self.json_path:
            with open(self.json_path, mode="w", encoding="utf-8") as file:
                json.dump(
                    self.filtered_items,
                    file,
                    ensure_ascii=False,
                    indent=4
                )

            spider.logger.info(f"Export JSON terminé : {self.json_path}")

        self.conn.close()

    @staticmethod
    def slugify(value):
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        value = value.strip("_")
        return value
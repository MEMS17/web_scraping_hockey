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

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

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
            adapter.get("team_name"),
            adapter.get("year"),
            adapter.get("wins"),
            adapter.get("losses"),
            adapter.get("ot_losses"),
            adapter.get("win_percentage"),
            adapter.get("goals_for"),
            adapter.get("goals_against"),
            adapter.get("goal_difference"),
            adapter.get("source_url"),
        ))

        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.conn.close()
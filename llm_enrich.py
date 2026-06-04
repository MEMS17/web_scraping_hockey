import argparse
import json
import os
import sqlite3
from pathlib import Path
from urllib import request

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "hockey_scraper" / "hockey_teams.db"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


def normalize_text(value):
    if value is None:
        return ""

    return " ".join(
        value.lower()
        .replace(".", "")
        .replace(",", "")
        .replace("-", " ")
        .split()
    )


def ensure_table(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hockey_team_llm_enrichment (
            team_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            canonical_team_name TEXT NOT NULL,
            city_or_region TEXT NOT NULL,
            nickname TEXT NOT NULL,
            performance_note_fr TEXT NOT NULL,
            model TEXT NOT NULL,
            raw_response_json TEXT NOT NULL,
            PRIMARY KEY (team_name, year)
        )
        """
    )
    conn.commit()


def load_rows(conn, limit):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            t.team_name,
            t.year,
            t.wins,
            t.losses,
            t.ot_losses,
            t.win_percentage,
            t.goals_for,
            t.goals_against,
            t.goal_difference
        FROM hockey_teams t
        LEFT JOIN hockey_team_llm_enrichment e
            ON e.team_name = t.team_name
           AND e.year = t.year
        WHERE e.team_name IS NULL
        ORDER BY t.year, t.team_name
        LIMIT ?
        """,
        (limit,),
    )
    return cursor.fetchall()


def build_prompt(row):
    team_name, year, wins, losses, ot_losses, win_percentage, goals_for, goals_against, goal_difference = row

    return f"""
                Tu enrichis une ligne de palmarès de hockey.
                Retourne uniquement un JSON valide.

                Contraintes :
                    - N'invente aucun fait externe.
                    - Utilise seulement les données fournies.
                    - `canonical_team_name` doit rester le même nom d'équipe, juste nettoyé si besoin.
                    - `city_or_region` = la partie géographique du nom.
                    - `nickname` = la partie "surnom / franchise" du nom.
                    - `performance_note_fr` = une phrase courte en français, factuelle, basée uniquement sur les stats.

                Champs attendus :
                {{
                    "canonical_team_name": "string",
                    "city_or_region": "string",
                    "nickname": "string",
                    "performance_note_fr": "string"
                }}

                Données :
                    - team_name: {team_name}
                    - year: {year}
                    - wins: {wins}
                    - losses: {losses}
                    - ot_losses: {ot_losses}
                    - win_percentage: {win_percentage}
                    - goals_for: {goals_for}
                    - goals_against: {goals_against}
                    - goal_difference: {goal_difference}
                """.strip()


def parse_json_response(text):
    text = text.strip()

    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

    return json.loads(text)


def validate_payload(team_name, payload):
    required_fields = [
        "canonical_team_name",
        "city_or_region",
        "nickname",
        "performance_note_fr",
    ]

    for field in required_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Champ invalide : {field}")

    original_name = normalize_text(team_name)
    canonical_name = normalize_text(payload["canonical_team_name"])
    city = normalize_text(payload["city_or_region"])
    nickname = normalize_text(payload["nickname"])

    if canonical_name != original_name:
        raise ValueError("Le nom canonique ne correspond pas au nom d'origine")

    if city not in original_name:
        raise ValueError("La ville ou région ne correspond pas au nom d'origine")

    if nickname not in original_name:
        raise ValueError("Le surnom ne correspond pas au nom d'origine")

    if len(payload["performance_note_fr"]) > 180:
        raise ValueError("La note de performance est trop longue")


def call_mistral_api(api_key, model, prompt):
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Tu es un assistant d'extraction. Tu réponds uniquement avec du JSON valide.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0,
    }

    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        MISTRAL_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with request.urlopen(http_request, timeout=60) as response:
        response_payload = json.loads(response.read().decode("utf-8"))

    return response_payload["choices"][0]["message"]["content"]


def enrich_row(api_key, model, row):
    prompt = build_prompt(row)
    output_text = call_mistral_api(api_key, model, prompt)
    payload = parse_json_response(output_text)
    validate_payload(row[0], payload)
    return payload


def save_payload(conn, team_name, year, payload, model):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO hockey_team_llm_enrichment (
            team_name,
            year,
            canonical_team_name,
            city_or_region,
            nickname,
            performance_note_fr,
            model,
            raw_response_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(team_name, year) DO UPDATE SET
            canonical_team_name = excluded.canonical_team_name,
            city_or_region = excluded.city_or_region,
            nickname = excluded.nickname,
            performance_note_fr = excluded.performance_note_fr,
            model = excluded.model,
            raw_response_json = excluded.raw_response_json
        """,
        (
            team_name,
            year,
            payload["canonical_team_name"],
            payload["city_or_region"],
            payload["nickname"],
            payload["performance_note_fr"],
            model,
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    conn.commit()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--model", default="mistral-small-latest")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv(PROJECT_DIR / ".env")

    if not Path(args.db_path).exists():
        raise FileNotFoundError(f"Base introuvable: {args.db_path}")

    conn = sqlite3.connect(args.db_path)
    ensure_table(conn)

    rows = load_rows(conn, args.limit)
    print(f"{len(rows)} lignes à enrichir")

    if args.dry_run or not rows:
        conn.close()
        return

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        conn.close()
        raise EnvironmentError("La variable MISTRAL_API_KEY est absente")

    for row in rows:
        team_name = row[0]
        year = row[1]
        print(f"Enrichissement : {team_name} ({year})")
        payload = enrich_row(api_key, args.model, row)
        save_payload(conn, team_name, year, payload, args.model)

    conn.close()


if __name__ == "__main__":
    main()

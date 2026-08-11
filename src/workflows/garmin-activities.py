from datetime import datetime, UTC

from dotenv import load_dotenv
from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from src.helpers import get_garmin_client, get_notion_client


def get_all_activities(
    garmin_client: GarminClient,
    limit: int = 10,
) -> list[dict]:
    return garmin_client.get_activities(0, limit)


def format_duration(seconds: float) -> float:
    """Convertit les secondes en minutes."""
    return round(seconds / 60, 2) if seconds else 0


def get_data_source_id(
    notion_client: NotionClient,
    database_id: str,
) -> str:
    """Récupère automatiquement la première data source de la database."""

    database = notion_client.request(
        path=f"databases/{database_id}",
        method="GET",
    )

    data_sources = database.get("data_sources", [])

    if not data_sources:
        raise ValueError(
            "Aucune data source trouvée dans la database Notion."
        )

    return data_sources[0]["id"]


def activity_exists(
    notion_client: NotionClient,
    data_source_id: str,
    activity_name: str,
) -> bool:
    """Vérifie si une sortie existe déjà."""

    response = notion_client.request(
        path=f"data_sources/{data_source_id}/query",
        method="POST",
        body={
            "filter": {
                "property": "Sortie",
                "title": {
                    "equals": activity_name
                }
            }
        },
    )

    return len(response.get("results", [])) > 0


def create_activity(
    notion_client: NotionClient,
    data_source_id: str,
    activity: dict,
) -> None:
    """Crée une sortie dans Notion."""

    activity_name = activity.get(
        "activityName",
        "Sortie Garmin",
    )

    start_time = activity.get("startTimeGMT")

    if not start_time:
        print(f"⚠️ Date absente pour : {activity_name}")
        return

    activity_date = datetime.strptime(
        start_time,
        "%Y-%m-%d %H:%M:%S",
    ).replace(tzinfo=UTC)

    properties = {
        "Sortie": {
            "title": [
                {
                    "text": {
                        "content": activity_name
                    }
                }
            ]
        },
        "Date": {
            "date": {
                "start": activity_date.isoformat()
            }
        },
        "Distance": {
            "number": round(
                activity.get("distance", 0) / 1000,
                2,
            )
        },
        "Durée": {
            "number": format_duration(
                activity.get("duration", 0)
            )
        },
        "Type de séance": {
            "select": {
                "name": activity.get(
                    "activityType",
                    {}).get(
                    "typeKey",
                    "Autre",
                )
            }
        },
        "D+": {
            "number": round(
                activity.get(
                    "elevationGain",
                    0,
                )
            )
        },
        "FC moyenne": {
            "number": round(
                activity.get(
                    "averageHR",
                    0,
                )
            )
        },
        "FC max": {
            "number": round(
                activity.get(
                    "maxHR",
                    0,
                )
            )
        },
        "Cadence moyenne": {
            "number": round(
                activity.get(
                    "averageRunningCadenceInStepsPerMinute",
                    activity.get(
                        "averageBikingCadenceInRevPerMinute",
                        0,
                    ),
                ),
                1,
            )
        },
    }

    notion_client.pages.create(
        parent={
            "data_source_id": data_source_id
        },
        properties=properties,
    )

    print(f"✅ Ajoutée : {activity_name}")


def main():
    load_dotenv()

    print("=== GARMIN → NOTION ===")

    # Garmin
    print("Initialisation Garmin...")
    garmin_client, garmin_configuration = get_garmin_client()

    # Notion
    print("Initialisation Notion...")
    notion_client, notion_dbs = get_notion_client()

    database_id = notion_dbs.activities

    print(f"Database Notion : {database_id}")

    # Récupération automatique de la data source
    data_source_id = get_data_source_id(
        notion_client,
        database_id,
    )

    print(f"Data source : {data_source_id}")

    # Récupération Garmin
    activities = get_all_activities(
        garmin_client,
        garmin_configuration.activity_fetch_limit,
    )

    print(f"{len(activities)} activité(s) récupérée(s) depuis Garmin.")

    # Synchronisation
    for activity in activities:

        activity_name = activity.get(
            "activityName",
            "Sortie Garmin",
        )

        if activity_exists(
            notion_client,
            data_source_id,
            activity_name,
        ):
            print(f"⏭️ Déjà présente : {activity_name}")
            continue

        create_activity(
            notion_client,
            data_source_id,
            activity,
        )

    print("=== SYNCHRONISATION TERMINÉE ===")


if __name__ == "__main__":
    main()

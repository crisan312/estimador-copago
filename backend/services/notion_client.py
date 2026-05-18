"""
Notion MCP client para fetch de pólizas.
Activo solo cuando NOTION_API_KEY y NOTION_POLICIES_DB_ID están configurados.
"""
import aiohttp
from config import settings


async def fetch_policy(policy_number: str) -> dict | None:
    if not settings.notion_enabled:
        return None

    headers = {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "filter": {
            "property": "numero_poliza",
            "rich_text": {"equals": policy_number},
        }
    }
    url = f"https://api.notion.com/v1/databases/{settings.notion_policies_db_id}/query"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            results = data.get("results", [])
            if not results:
                return None
            return _parse_notion_page(results[0])


def _parse_notion_page(page: dict) -> dict:
    props = page.get("properties", {})

    def text(key: str) -> str:
        items = props.get(key, {}).get("rich_text", [])
        return items[0]["plain_text"] if items else ""

    def number(key: str) -> float:
        return props.get(key, {}).get("number") or 0.0

    def checkbox(key: str) -> bool:
        return props.get(key, {}).get("checkbox", False)

    def title(key: str = "nombre") -> str:
        items = props.get(key, {}).get("title", [])
        return items[0]["plain_text"] if items else ""

    return {
        "plan_nombre": title("nombre"),
        "aseguradora": text("aseguradora"),
        "deducible_anual": number("deducible_anual"),
        "deducible_consumido": number("deducible_consumido"),
        "copago_pct": number("copago_pct"),
        "coaseguro_pct": number("coaseguro_pct"),
        "cobertura_consulta_externa": checkbox("cobertura_consulta_externa"),
        "cobertura_especialistas": checkbox("cobertura_especialistas"),
        "cobertura_emergencias": checkbox("cobertura_emergencias"),
        "tope_anual_usd": number("tope_anual_usd") or None,
        "tope_consumido_usd": number("tope_consumido_usd"),
        "red_hospitales_autorizados": [],
        "fuente": "notion",
    }

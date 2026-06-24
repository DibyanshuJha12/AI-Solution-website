from __future__ import annotations

from markupsafe import Markup, escape

from ..models import SiteSetting


def active_settings_map() -> dict[str, str]:
    items = (
        SiteSetting.query.filter_by(active=True, archived=False)
        .order_by(SiteSetting.category.asc(), SiteSetting.key.asc())
        .all()
    )
    return {item.key: item.value_text for item in items}


def setting_value(settings: dict[str, str], key: str, default: str = "") -> str:
    return settings.get(key, default)


def split_list_text(value: str | None) -> list[str]:
    if not value:
        return []
    return [line.strip() for line in value.replace("\r", "").split("\n") if line.strip()]


def markdownish(value: str | None) -> Markup:
    if not value:
        return Markup("")

    lines = [line.rstrip() for line in value.replace("\r", "").split("\n")]
    chunks: list[str] = []
    list_open = False

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            chunks.append("</ul>")
            list_open = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            close_list()
            continue
        if line.startswith("## "):
            close_list()
            chunks.append(f"<h2>{escape(line[3:])}</h2>")
            continue
        if line.startswith("- "):
            if not list_open:
                chunks.append("<ul>")
                list_open = True
            chunks.append(f"<li>{escape(line[2:])}</li>")
            continue
        close_list()
        chunks.append(f"<p>{escape(line)}</p>")

    close_list()
    return Markup("\n".join(chunks))

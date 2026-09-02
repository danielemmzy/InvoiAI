from __future__ import annotations

from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)


class TemplateRenderer:
    """
    Central Jinja2 notification template renderer.

    Templates are stored under:

        app/
            templates/
                email/
                    *.html
                    *.txt
    """

    def __init__(self) -> None:

        template_path = (
            Path(__file__)
            .resolve()
            .parents[2]
            / "templates"
            / "email"
        )

        self.environment = Environment(
            loader=FileSystemLoader(
                template_path,
            ),
            autoescape=select_autoescape(
                enabled_extensions=(
                    "html",
                    "xml",
                ),
            ),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # =========================================================
    # Generic
    # =========================================================

    def render(
        self,
        *,
        template_name: str,
        context: dict,
    ) -> str:

        template = self.environment.get_template(
            template_name,
        )

        return template.render(
            **context,
        )

    # =========================================================
    # HTML
    # =========================================================

    def render_html(
        self,
        *,
        template: str,
        context: dict,
    ) -> str:

        return self.render(
            template_name=f"{template}.html",
            context=context,
        )

    # =========================================================
    # Plain Text
    # =========================================================

    def render_text(
        self,
        *,
        template: str,
        context: dict,
    ) -> str:

        return self.render(
            template_name=f"{template}.txt",
            context=context,
        )

    # =========================================================
    # Preview
    # =========================================================

    def preview(
        self,
        *,
        template: str,
        context: dict,
    ) -> dict[str, str]:

        return {
            "html": self.render_html(
                template=template,
                context=context,
            ),
            "text": self.render_text(
                template=template,
                context=context,
            ),
        }
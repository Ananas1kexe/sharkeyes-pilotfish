import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

from main import app


def generate_documentation() -> None:
    output_dir = Path(__file__).resolve().parent.parent / "docs" / "dev"
    output_dir.mkdir(parents=True, exist_ok=True)

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    json_path = output_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    redoc_html = f"""<!DOCTYPE html>
<html>
  <head>
    <title>{app.title} - Dev Docs</title>

    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>body {{ margin: 0; padding: 0; }}</style>
  </head>
  <body>
    <redoc spec-url='openapi.json'></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
  </body>
</html>"""

    html_path = output_dir / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(redoc_html)

    print(f"Documentation generated successfully in: {output_dir}")


if __name__ == "__main__":
    generate_documentation()
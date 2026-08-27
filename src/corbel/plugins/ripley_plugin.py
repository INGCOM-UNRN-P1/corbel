"""Plugin de CORBEL para el microkernel RIPLEY."""

from pathlib import Path
from typing import Dict, Any
from corbel.core.doc_parser import parse_header_documentation
from corbel.core.renderers import render_markdown


class CorbelPlugin:
    """Plugin de generación de documentación para Ripley."""

    name = "documentation"
    description = "Generación de documentación automática de APIs y TDAs en Markdown/man pages"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        source_dir = Path(context.get("source_dir", "."))
        headers = list(source_dir.glob("*.h"))
        docs_generated = []

        for h in headers:
            doc = parse_header_documentation(h)
            md = render_markdown(doc)
            out_file = source_dir / f"{h.stem}_API.md"
            out_file.write_text(md, encoding="utf-8")
            docs_generated.append(str(out_file))

        return {
            "passed": True,
            "headers_documented": len(headers),
            "generated_files": docs_generated
        }

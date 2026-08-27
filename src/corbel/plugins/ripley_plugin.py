"""Plugin de CORBEL para el microkernel RIPLEY."""

from pathlib import Path
from typing import Dict, Any
from corbel.core.doc_parser import parse_header_documentation
from corbel.core.renderers import render_markdown
from corbel.core.placeholder import inject_placeholders, analyze_missing_documentation


class CorbelPlugin:
    """Plugin de generación y scaffolding de documentación para Ripley."""

    name = "documentation"
    description = "Generación de documentación automática de APIs, TDAs y scaffolding de placeholders Doxygen"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        source_dir = Path(context.get("source_dir", "."))
        headers = list(source_dir.glob("*.h"))
        scaffold_mode = context.get("scaffold", False) or context.get("placeholders", False)
        docs_generated = []
        scaffolded_files = []
        total_missing = 0

        for h in headers:
            code = h.read_text(encoding="utf-8", errors="replace")
            missing = analyze_missing_documentation(code, h.name)
            total_missing += len(missing)

            if scaffold_mode:
                updated = inject_placeholders(code, h.name)
                h.write_text(updated, encoding="utf-8")
                scaffolded_files.append(str(h))
            else:
                doc = parse_header_documentation(h)
                md = render_markdown(doc)
                out_file = source_dir / f"{h.stem}_API.md"
                out_file.write_text(md, encoding="utf-8")
                docs_generated.append(str(out_file))

        return {
            "passed": True,
            "headers_documented": len(headers),
            "generated_files": docs_generated,
            "scaffolded_files": scaffolded_files,
            "total_missing_elements": total_missing
        }

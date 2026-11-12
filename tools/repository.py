"""The three ordinary Python functions the agent can request."""
from ._source import MAX_RESULT, Source


class RepositoryTools(Source):
    def list_files(self) -> dict:
        """List the available relative source paths."""
        paths = sorted(self.files)
        shown = []
        for path in paths:
            if sum(len(p) + 1 for p in shown) + len(path) > MAX_RESULT:
                break
            shown.append(path)
        return {
            "paths": shown,
            "truncated": len(shown) < len(paths),
            "selected_files": len(paths),
        }

    def read_file(
        self, path: str, start_line: int = 1, end_line: int = 80
    ) -> dict:
        """Read a source slice with line numbers (80 lines, 6000 chars max)."""
        try:
            lines = self.lines(path)
            if (
                type(start_line) is not int
                or type(end_line) is not int
                or not 1 <= start_line <= end_line
                or start_line > max(1, len(lines))
            ):
                raise ValueError("Use a valid inclusive 1-based line range")
            end = min(end_line, start_line + 79, len(lines))
            content = "\n".join(
                f"{i + 1}: {lines[i]}" for i in range(start_line - 1, end)
            )
            return {
                "path": path,
                "content": content[:MAX_RESULT],
                "total_lines": len(lines),
                "truncated": end < min(end_line, len(lines))
                or len(content) > MAX_RESULT,
            }
        except (ValueError, TypeError) as error:
            return {"error": str(error)}

    def search_code(self, query: str) -> dict:
        """Search source for literal text; return matching paths and lines."""
        if not isinstance(query, str) or not 1 <= len(query) <= 200:
            return {"error": "Use a literal query of 1–200 characters"}
        hits = []
        size = 0
        for path in sorted(self.files):
            for number, line in enumerate(self.lines(path), 1):
                if query in line:
                    hit = {"path": path, "line": number, "text": line[:300]}
                    size += len(str(hit))
                    if len(hits) >= 30 or size > MAX_RESULT:
                        return {"matches": hits, "truncated": True}
                    hits.append(hit)
        return {"matches": hits, "truncated": False}

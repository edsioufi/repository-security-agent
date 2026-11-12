"""Accept a structured final report; validation does not prove accuracy."""
from google.adk.tools import ToolContext
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    cwe: str = Field(pattern=r"^CWE-[1-9][0-9]*$")
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    evidence: str = Field(min_length=1, max_length=3000)
    explanation: str = Field(min_length=1, max_length=3000)
    fix: str = Field(min_length=1, max_length=1000)


class ReportTool:
    def __init__(self, source):
        self.source = source
        self.accepted = None

    def submit_report(
        self, findings: list[Finding], coverage: list[str],
        limitations: str, tool_context: ToolContext,
    ) -> dict:
        """Finish with supported findings, inspected paths, and limitations.

        Cite exact source text as evidence. An empty findings list is valid.
        Use CWE identifiers, existing paths, and inclusive source line ranges.
        Rejected reports can be corrected within the remaining call budget.
        """
        try:
            if not coverage or not limitations.strip():
                raise ValueError("Provide coverage and honest limitations")
            for path in coverage:
                self.source.lines(path)
            checked = []
            for item in findings:
                item = Finding.model_validate(item)
                lines = self.source.lines(item.path)
                if not item.start_line <= item.end_line <= len(lines):
                    raise ValueError("Source range does not exist")
                if item.path not in coverage:
                    raise ValueError("Finding path must appear in coverage")
                excerpt = "\n".join(
                    lines[item.start_line - 1:item.end_line]
                )
                if item.evidence not in excerpt:
                    raise ValueError("Evidence must quote the cited source")
                checked.append(item.model_dump())
            self.accepted = {
                "findings": checked, "coverage": sorted(set(coverage)),
                "limitations": limitations,
            }
            tool_context.actions.skip_summarization = True
            return {"accepted": True}
        except (ValueError, TypeError, ValidationError) as error:
            return {"accepted": False, "error": str(error)[:1500]}

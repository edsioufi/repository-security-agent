"""Deterministic model fixture for testing real ADK tool execution."""
from pydantic import PrivateAttr
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class ScriptedModel(BaseLlm):
    model: str = "offline-scripted"
    _step: int = PrivateAttr(default=0)
    _path: str = PrivateAttr(default="")

    async def generate_content_async(self, llm_request, stream=False):
        self._step += 1
        responses = [
            p.function_response
            for c in llm_request.contents for p in c.parts or []
            if p.function_response
        ]
        if self._step == 1:
            name, args = "list_files", {}
        elif self._step == 2:
            paths = responses[-1].response.get("paths", [])
            self._path = next((p for p in paths if p.endswith(".py")), "")
            name, args = "read_file", {"path": self._path}
        elif self._step == 3:
            name, args = "search_code", {"query": "lookup"}
        else:
            read = next(
                (r.response for r in responses if r.name == "read_file"), {}
            )
            evidence = read.get("content", read.get("error", "No evidence"))
            text = (
                "OFFLINE: scripted plumbing demonstration, not an AI review.\n"
                f"The read_file tool returned this for {self._path}:\n"
                f"{evidence}\n"
                "The search_code result was also returned to the model.\n"
                "A live model uses this evidence to decide what to read next "
                "and explain its findings. No security conclusion is made here."
            )
            yield LlmResponse(content=types.Content(
                role="model", parts=[types.Part.from_text(text=text)],
            ))
            return
        yield LlmResponse(content=types.Content(
            role="model", parts=[types.Part(function_call=types.FunctionCall(
                name=name, args=args,
            ))],
        ))

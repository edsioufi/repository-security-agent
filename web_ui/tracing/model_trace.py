"""Expose visible model messages, never credentials or private reasoning."""


def visible_content(content):
    if content is None:
        return None
    value = content.model_dump(mode="json", exclude_none=True)
    value["parts"] = [
        {key: part[key] for key in ("text", "function_call", "function_response")
         if key in part}
        for part in value.get("parts", []) if not part.get("thought")
    ]
    return value


def attach_trace(agent, emit, max_calls=8):
    """Install callbacks on a fresh UI agent; leave the CLI unchanged."""
    call = 0

    def before(callback_context, llm_request):
        nonlocal call
        # ADK invokes this callback before its own call-limit check.
        if call >= max_calls:
            raise RuntimeError("Model call limit reached")
        call += 1
        config = llm_request.config
        instruction = config.system_instruction if config else None
        if hasattr(instruction, "model_dump"):
            instruction = visible_content(instruction)
        schemas = []
        for tool in (config.tools or []) if config else []:
            if hasattr(tool, "function_declarations"):
                schemas.extend(
                    declaration.model_dump(mode="json", exclude_none=True)
                    for declaration in tool.function_declarations or []
                )
        emit("LLM INPUT", {
            "call": call,
            "system_instruction": instruction,
            "tools": schemas,
            "messages": [visible_content(c) for c in llm_request.contents],
        })

    def after(callback_context, llm_response):
        emit("LLM OUTPUT", {
            "call": call,
            "content": visible_content(llm_response.content),
            "finish_reason": str(llm_response.finish_reason or ""),
            "error_code": llm_response.error_code,
            "usage": (llm_response.usage_metadata.model_dump(
                mode="json", exclude_none=True,
            ) if llm_response.usage_metadata else None),
        })

    agent.before_model_callback = before
    agent.after_model_callback = after

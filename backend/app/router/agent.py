"""真正的 ReAct Agent 流式接口。"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.integration.react_agent import ReactAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRequest(BaseModel):
    message: str
    history: list[dict] = []
    session_id: int | str | None = None


@router.post("/stream")
def agent_stream(request: AgentRequest):
    """真正的 ReAct Agent 流式接口（SSE）。

    输出事件类型：
    - thinking:    LLM 思考过程文字
    - tool_call:   工具调用（工具名 + 参数）
    - tool_result: 工具执行结果（来源 + 预览）
    - answer:      最终答案（含数据来源列表）
    - error:       错误信息
    """
    def event_generator():
        agent = ReactAgent()
        try:
            for event in agent.stream(request.message, history=request.history):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("agent_stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router"]

"""智能问数专用路由"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.integration.langgraph_agent import LangGraphAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    """问数请求"""
    message: str
    history: list[dict] = []
    session_id: str | None = None


@router.post("/stream")
def query_stream(request: QueryRequest):
    """智能问数流式接口（SSE）

    输出事件类型：
    - tool_call: 工具调用
    - tool_result: 工具结果
    - status: 状态更新
    - answer: 最终答案
    - clarification: 澄清追问
    """
    def event_generator():
        agent = LangGraphAgent()

        try:
            # 检测是否需要澄清
            for event in agent.stream(
                request.message,
                history=request.history,
                max_iterations=10,
            ):
                event_type = event.get("type")

                if event_type == "tool_call":
                    # 工具调用事件
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': event.get('tool'), 'args': event.get('args')}, ensure_ascii=False)}\n\n"

                elif event_type == "tool_result":
                    # 工具结果事件
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': event.get('tool'), 'preview': event.get('content', '')[:200]}, ensure_ascii=False)}\n\n"

                elif event_type == "status":
                    # 状态更新事件
                    yield f"data: {json.dumps({'type': 'status', 'content': event.get('content')}, ensure_ascii=False)}\n\n"

                elif event_type == "answer":
                    # 最终答案事件
                    content = event.get("content", "")
                    dual_model_used = event.get("dual_model_used", False)

                    # 检测澄清标记
                    if "[CLARIFY]" in content:
                        clarification_question = content.replace("[CLARIFY]", "").strip()
                        yield f"data: {json.dumps({'type': 'clarification', 'question': clarification_question}, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'answer', 'content': content, 'clarification_needed': False, 'dual_model_used': dual_model_used}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except Exception as exc:
            logger.exception("query_stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': f'查询出错：{exc}'}, ensure_ascii=False)}\n\n"

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

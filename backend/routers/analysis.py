import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.utils import dumps

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analysis/stream")
async def analysis_stream(question: str):
    from backend.services.streaming import run_pipeline_streaming

    async def event_generator():
        try:
            async for item in run_pipeline_streaming(question):
                event_type = item.get("type", "log")

                if event_type == "_heartbeat":
                    yield ": heartbeat\n\n"
                    continue

                payload = {k: v for k, v in item.items() if k != "type"}
                serialized = dumps(payload)

                if event_type == "result":
                    logger.info(f"[SSE] result event size: {len(serialized)} bytes")

                yield f"event: {event_type}\ndata: {serialized}\n\n"

        except Exception as e:
            logger.exception(f"[SSE] pipeline error: {e}")
            yield f"event: error\ndata: {dumps({'message': str(e)})}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

from fastapi import APIRouter
import uuid
from src.stream_dataset import stream_csv_pipeline
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo"])

@router.post("/start")
async def start_demo():

    demo_id = f"demo_{uuid.uuid4().hex[:8]}"
    logger.info(f"Demo started: {demo_id}")
    logger.info(f"Launching replay task for {demo_id}")
    asyncio.create_task(
        stream_csv_pipeline(
            line_id_override=demo_id
        )
    )
    
    return {
        "status": "started",
        "demo_line_id": demo_id
    }
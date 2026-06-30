# data/stream_dataset.py
import asyncio
import csv
import logging
import time
import httpx
import uuid

DEMO_LINE_ID = f"demo_{uuid.uuid4().hex[:8]}"

DEMO_MODE = True


# Configure logging to monitor real-time pipeline velocity metrics
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TelemetryStreamer")

API_URL = "http://localhost:8000/readings"
# API_URL = "https://lineguard-webapi.onrender.com/readings"
# CSV_FILE_PATH = "data/sensor_data.csv"
CSV_FILE_PATH = "data/demo_sensor_data.csv"



async def send_sensor_reading(
    client: httpx.AsyncClient, payload: dict, semaphore: asyncio.Semaphore
):
    """
    Executes an individual HTTP POST request inside the semaphore boundary.
    """
    async with semaphore:
        try:
            response = await client.post(API_URL, json=payload, timeout=5.0)
            if response.status_code == 200:
                status = response.json().get("status")
                if status == "ignored":
                    logger.debug(
                        f"Idempotent duplicate dropped safely: {payload['sensor_type']}"
                    )
                else:
                    logger.debug(f"Telemetry record saved: {payload['sensor_type']}")
            else:
                logger.error(
                    f"API rejection error code {response.status_code}: {response.text}"
                )
        except httpx.RequestError as exc:
            logger.error(f"Network transport level collision failure: {exc}")


async def stream_csv_pipeline(
        line_id_override: str | None = None
):
    """
    Streams the wide factory dataset line-by-line, converts records to narrow formats,
    and enforces a strict rate limit of 100 CSV rows/sec using periodic batch clearing.
    """
    # Enforce an active concurrency barrier to prevent socket allocation starvation
    semaphore = asyncio.Semaphore(150)
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=200)

    # Track persistent task collections to prevent early exit truncation
    active_tasks = []
    MAX_MEMORY_BATCH_SIZE = 1000  # Automatically flushes tasks to prevent memory bloat

    async with httpx.AsyncClient(limits=limits) as client:
        try:
            with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                total_rows_processed = 0
                batch_start_time = time.time()
                batch_row_count = 0

                logger.info(
                    "Initializing production telemetry replay engine at 100 rows/sec (300 events/sec)..."
                )

                for row in reader:
                    line_id = (
                        line_id_override
                        if line_id_override is not None
                        else (
                            DEMO_LINE_ID
                            if DEMO_MODE
                            else row["line_id"]
                        )
                    )
                    timestamp_raw = row["timestamp"]

                    # Normalizing columns into independent narrow metrics arrays
                    sensors_to_extract = [
                        {"type": "torque", "value": float(row["torque"])},
                        {
                            "type": "conveyor_speed",
                            "value": float(row["conveyor_speed"]),
                        },
                        {"type": "fill_level", "value": float(row["fill_level"])},
                    ]

                    for sensor in sensors_to_extract:
                        payload = {
                            "line_id": line_id,
                            "sensor_type": sensor["type"],
                            "value": sensor["value"],
                            "timestamp": timestamp_raw,
                        }

                        # FIX: Schedule the task AND store its tracking reference securely
                        task = asyncio.create_task(
                            send_sensor_reading(client, payload, semaphore)
                        )
                        active_tasks.append(task)

                    batch_row_count += 1
                    total_rows_processed += 1

                    # Memory Protection Filter: Periodically drain task array to avoid memory bloat
                    if len(active_tasks) >= MAX_MEMORY_BATCH_SIZE:
                        await asyncio.gather(*active_tasks)
                        active_tasks.clear()

                    # FIX: Throttling now tracks true CSV rows/sec instead of narrow event counts
                    if batch_row_count >= 100:
                        elapsed_time = time.time() - batch_start_time
                        if elapsed_time < 1.0:
                            sleep_needed = 1.0 - elapsed_time
                            await asyncio.sleep(sleep_needed)

                        # Reset the batch timer window variables
                        batch_start_time = time.time()
                        batch_row_count = 0
                        logger.info(
                            f"Sustained pipeline progress tracking: Sent {total_rows_processed} wide rows."
                        )

                # FIX: Final Flush Sequence
                # Await any remaining tasks left in the array after the file reader finishes
                if active_tasks:
                    logger.info(
                        f"File parsing complete. Draining final {len(active_tasks)} sensor events..."
                    )
                    await asyncio.gather(*active_tasks)
                    active_tasks.clear()

                logger.info(
                    f"Stream ingestion run finished. Successfully committed {total_rows_processed} wide rows."
                )

        except FileNotFoundError:
            logger.critical(
                f"Target simulation file missing at layout coordinate path: {CSV_FILE_PATH}"
            )


if __name__ == "__main__":
    asyncio.run(stream_csv_pipeline())

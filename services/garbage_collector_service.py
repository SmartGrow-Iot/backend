import asyncio
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from firebase_config import initialize_firebase_admin, get_firestore_db
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gc_service")

initialize_firebase_admin()
db = get_firestore_db()

# List of collections and their timestamp field names to clean up.
COLLECTIONS_TO_CLEAN = {
    "ActionLog": "timestamp",
    "EnvironmentalData": "timestamp"
}

def delete_collection_batch(db, collection_name: str, timestamp_field: str, cutoff_timestamp: datetime):
    """
    The core logic for querying and deleting ActionLog and EnvironmentalData documents.
    This is a synchronous function called by our async task.
    """
    logger.info(f"[{datetime.now(timezone.utc).isoformat()}] GC: Starting deletion for '{collection_name}'...")

    docs_to_delete_query = db.collection(collection_name).where(timestamp_field, "<", cutoff_timestamp).select([])
    docs = docs_to_delete_query.stream()

    batch = db.batch()
    deleted_count = 0
    batch_count = 0

    for doc in docs:
        batch.delete(doc.reference)
        deleted_count += 1
        batch_count += 1

        # Firestore limitation, single batch can hold max 500 operations
        if batch_count >= 499:
            batch.commit()
            batch = db.batch()
            batch_count = 0

    # Delete final leftover batch
    if batch_count > 0:
        batch.commit()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] GC: Finished. Deleted {deleted_count} documents from '{collection_name}'.")


async def run_garbage_collector():
    """
    An async task that runs forever, triggering the cleanup job at the correct time.
    """
    logger.info("Garbage Collector background task started.")

    while True:
        try:
            # Calculate the next run time (midnight UTC)
            now_utc = datetime.now(timezone.utc)
            tomorrow_utc = now_utc.date() + timedelta(days=1)
            next_run_time = datetime.combine(tomorrow_utc, datetime.min.time(), tzinfo=timezone.utc)

            sleep_seconds = (next_run_time - now_utc).total_seconds()

            logger.info(
                f"GC: Next cleanup scheduled at {next_run_time.isoformat()}. Sleeping for {sleep_seconds:.2f} seconds.")

            # Sleep until the next run time
            await asyncio.sleep(sleep_seconds)

            # Run the job
            logger.info(f"[{datetime.now(timezone.utc).isoformat()}] GC: Run daily cleanup job.")

            # Cutoff time 7 days - today Friday (27/6/2025), delete all logs prior to last Friday (20/6/2025)
            today_utc = datetime.now(timezone.utc).date()
            cutoff_timestamp = datetime.combine(today_utc, datetime.min.time(), tzinfo=timezone.utc) - timedelta(
                days=7)

            for collection, timestamp_field in COLLECTIONS_TO_CLEAN.items():
                delete_collection_batch(db, collection, timestamp_field, cutoff_timestamp)

            logger.info(f"[{datetime.now(timezone.utc).isoformat()}] GC: Daily cleanup job finished.")

        except asyncio.CancelledError:
            logger.info("Garbage Collector task is being cancelled. Shutting down gracefully.")
            break
        except Exception as e:
            logger.warning(f"An error occurred in the Garbage Collector task: {e}")
            await asyncio.sleep(60)

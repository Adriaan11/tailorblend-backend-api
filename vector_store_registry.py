"""
Vector Store Registry & Management

Manages OpenAI vector stores for ingredient/base mix embeddings.
Tracks metadata in-memory with JSON file persistence.
Supports multiple datasets that users can upload and switch between.

Flow:
1. Startup: Load registry from JSON file OR rebuild from OpenAI
2. User uploads JSON: Convert to markdown, upload to OpenAI, create vector store
3. Chat: Use active vector store ID with FileSearchTool for ingredient lookups
4. Session: Track which vector store is active for each session

Vector stores live on OpenAI's servers (persistent).
Registry just tracks metadata in-memory + JSON file for recovery.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import aiofiles
from pydantic import BaseModel, Field
from openai import OpenAI, APIError

# Configure module logger
logger = logging.getLogger(__name__)

# ============================================================================
# Data Models
# ============================================================================

class VectorStoreMetadata(BaseModel):
    """Metadata about a single vector store"""
    id: str = Field(..., description="Unique identifier (uuid)")
    vector_store_id: str = Field(..., description="OpenAI's vector store ID (vs_xyz)")
    name: str = Field(..., description="Display name")
    source_file: str = Field(..., description="Original JSON filename (for reference)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    item_count: int = Field(default=0, description="Approximate number of items in store")


# ============================================================================
# Vector Store Registry
# ============================================================================

class VectorStoreRegistry:
    """
    Registry of all available vector stores.

    Maintains in-memory dict of VectorStoreMetadata.
    Persists to JSON file for recovery across restarts.
    Syncs with OpenAI to verify stores still exist.
    """

    # In-memory registry (loaded on startup)
    _registry: Dict[str, VectorStoreMetadata] = {}

    # Lock to prevent race conditions during initialization
    _init_lock = asyncio.Lock()

    # Path to persist registry
    _registry_file = Path(__file__).parent / "data" / "vector_stores_registry.json"

    @classmethod
    async def initialize_on_startup(cls) -> None:
        """
        Initialize registry on application startup.

        Hybrid approach:
        1. Try to load from JSON file (fast)
        2. Sync with OpenAI to verify stores still exist
        3. If no file, create default vector store from ingredients/base mixes

        This ensures registry is always in sync with OpenAI.
        """
        async with cls._init_lock:
            logger.info("🔄 [STARTUP] Initializing vector store registry...")

            try:
                # Step 1: Load from JSON file if it exists
                if cls._registry_file.exists():
                    await cls._load_from_file()
                    logger.info(f"✅ Loaded {len(cls._registry)} stores from file")
                else:
                    logger.info("📁 No registry file found, starting fresh")

                # Step 2: Sync with OpenAI (verify all stores exist)
                await cls._sync_with_openai()

                # Step 3: If no stores, create default
                if not cls._registry:
                    logger.info("⚠️  No vector stores found. Creating default...")
                    await cls._create_default_vector_store()

                logger.info(f"✅ [STARTUP] Registry ready: {len(cls._registry)} stores")

            except Exception as e:
                logger.error(f"❌ [STARTUP] Registry initialization failed: {e}", exc_info=True)
                raise

    @classmethod
    async def _load_from_file(cls) -> None:
        """Load registry from persisted JSON file."""
        try:
            async with aiofiles.open(cls._registry_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

            # Reconstruct VectorStoreMetadata objects
            for store_id, store_data in data.items():
                # Parse datetime string back to datetime
                store_data['created_at'] = datetime.fromisoformat(store_data['created_at'])
                metadata = VectorStoreMetadata(**store_data)
                cls._registry[store_id] = metadata
                logger.debug(f"  → Loaded: {metadata.name} ({metadata.vector_store_id})")

        except Exception as e:
            logger.warning(f"⚠️  Could not load registry from file: {e}")
            # Don't fail - we'll rebuild from OpenAI if needed

    @classmethod
    async def _sync_with_openai(cls) -> None:
        """
        Verify all stores in registry still exist on OpenAI.
        Remove any orphaned entries.
        """
        try:
            client = OpenAI()
            stores_on_openai = client.vector_stores.list()
            openai_store_ids = {store.id for store in stores_on_openai}

            # Find orphaned entries (in registry but not on OpenAI)
            orphaned = []
            for store_id, metadata in cls._registry.items():
                if metadata.vector_store_id not in openai_store_ids:
                    orphaned.append((store_id, metadata.name, metadata.vector_store_id))

            if orphaned:
                logger.warning(f"⚠️  Found {len(orphaned)} orphaned stores:")
                for reg_id, name, vs_id in orphaned:
                    logger.warning(f"   - {name} ({vs_id}) - removing from registry")
                    del cls._registry[reg_id]

            logger.debug(f"✅ Synced with OpenAI: {len(cls._registry)} valid stores")

        except APIError as e:
            logger.warning(f"⚠️  Could not sync with OpenAI: {e}")
            # Continue - use what we have in registry
        except Exception as e:
            logger.warning(f"⚠️  Error during sync: {e}")
            # Continue gracefully

    @classmethod
    async def _create_default_vector_store(cls) -> None:
        """
        Create default vector store from standard ingredients + base mixes.
        """
        try:
            from tb_agents.database_loader import load_ingredients_database, load_base_mixes_database

            logger.info("  → Creating default vector store...")

            # Get markdown content
            ingredients = await load_ingredients_database()
            base_mixes = await load_base_mixes_database()

            combined_content = f"{ingredients}\n\n{base_mixes}"

            # Upload to OpenAI
            client = OpenAI()

            logger.debug("    → Uploading content to OpenAI...")
            file_response = client.files.create(
                file=("default_ingredients_and_mixes.txt", combined_content.encode("utf-8")),
                purpose="assistants"
            )
            file_id = file_response.id
            logger.debug(f"    → File created: {file_id}")

            logger.debug("    → Creating vector store...")
            vs_response = client.vector_stores.create(
                name="default|111"  # Format: name|item_count
            )
            vector_store_id = vs_response.id
            logger.debug(f"    → Vector store created: {vector_store_id}")

            logger.debug("    → Indexing file (this may take a moment)...")
            client.vector_stores.files.create_and_poll(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            logger.debug(f"    → File indexed successfully")

            # Add to registry
            metadata = VectorStoreMetadata(
                id="default",
                vector_store_id=vector_store_id,
                name="Default Ingredients & Base Mixes",
                source_file="default_ingredients_and_mixes.txt",
                item_count=111
            )
            cls._registry["default"] = metadata

            # Persist to file
            await cls._save_to_file()

            logger.info("✅ Default vector store created successfully")

        except Exception as e:
            logger.error(f"❌ Failed to create default vector store: {e}", exc_info=True)
            raise

    @classmethod
    async def create_from_json(
        cls,
        json_content: str,
        name: str,
        source_filename: str
    ) -> VectorStoreMetadata:
        """
        Create new vector store from user-provided JSON content.

        Args:
            json_content: Raw JSON string
            name: Display name for the dataset
            source_filename: Original filename

        Returns:
            VectorStoreMetadata for the created store

        Raises:
            ValueError: If JSON is invalid
            APIError: If OpenAI API fails
        """
        try:
            logger.info(f"📤 Creating vector store from upload: {name}")

            # Validate JSON
            try:
                json.loads(json_content)
                logger.debug("  ✓ JSON valid")
            except json.JSONDecodeError as e:
                logger.error(f"  ✗ Invalid JSON: {e}")
                raise ValueError(f"Invalid JSON: {e}")

            # Convert JSON to markdown for better semantic search
            markdown_content = cls._json_to_markdown(json_content)
            item_count = len(json.loads(json_content))

            # Upload to OpenAI
            client = OpenAI()

            logger.debug("  → Uploading to OpenAI...")
            file_response = client.files.create(
                file=(source_filename, markdown_content.encode("utf-8")),
                purpose="assistants"
            )
            file_id = file_response.id
            logger.debug(f"  ✓ File uploaded: {file_id}")

            logger.debug("  → Creating vector store...")
            vs_response = client.vector_stores.create(
                name=f"{name}|{item_count}"  # Format: name|item_count
            )
            vector_store_id = vs_response.id
            logger.debug(f"  ✓ Vector store created: {vector_store_id}")

            logger.debug("  → Indexing file (this may take a moment)...")
            client.vector_stores.files.create_and_poll(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            logger.debug(f"  ✓ File indexed")

            # Create metadata
            metadata = VectorStoreMetadata(
                id=str(uuid.uuid4()),
                vector_store_id=vector_store_id,
                name=name,
                source_file=source_filename,
                item_count=item_count
            )

            # Add to registry
            cls._registry[metadata.id] = metadata

            # Persist
            await cls._save_to_file()

            logger.info(f"✅ Vector store created: {name} ({vector_store_id})")
            return metadata

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to create vector store: {e}", exc_info=True)
            raise APIError(f"Failed to create vector store: {e}")

    @classmethod
    async def create_from_multiple_files(
        cls,
        files: List,  # List[UploadFile] from FastAPI
        name: str
    ) -> VectorStoreMetadata:
        """
        Create new vector store from multiple user-provided files using batch upload.

        This method uses OpenAI's file_batches.upload_and_poll() for efficient
        concurrent upload and indexing of multiple files into a single vector store.

        Args:
            files: List of UploadFile objects (from FastAPI File upload)
            name: Display name for the dataset

        Returns:
            VectorStoreMetadata for the created store

        Raises:
            ValueError: If any JSON is invalid
            APIError: If OpenAI API fails
        """
        try:
            logger.info(f"📤 Creating vector store from {len(files)} files: {name}")

            client = OpenAI()
            vector_store_id = None

            try:
                # Step 1: Create empty vector store FIRST
                logger.debug("  → Creating vector store...")
                vs_response = client.beta.vector_stores.create(
                    name=f"{name}|multi"  # Temporary name, will update with item count
                )
                vector_store_id = vs_response.id
                logger.debug(f"  ✓ Vector store created: {vector_store_id}")

                # Step 2: Process and prepare all files
                file_tuples = []  # List of (filename, content_bytes) tuples
                total_items = 0
                source_filenames = []

                for upload_file in files:
                    # Read content
                    content = await upload_file.read()
                    content_str = content.decode('utf-8')

                    # Validate JSON
                    try:
                        data = json.loads(content_str)
                        if isinstance(data, list):
                            total_items += len(data)
                        else:
                            total_items += 1
                        logger.debug(f"  ✓ {upload_file.filename}: {len(data) if isinstance(data, list) else 1} items")
                    except json.JSONDecodeError as e:
                        logger.error(f"  ✗ Invalid JSON in {upload_file.filename}: {e}")
                        raise ValueError(f"Invalid JSON in {upload_file.filename}: {e}")

                    # Convert to markdown for better semantic search
                    markdown_content = cls._json_to_markdown(content_str)

                    # Prepare tuple for batch upload
                    file_tuples.append((upload_file.filename, markdown_content.encode("utf-8")))
                    source_filenames.append(upload_file.filename)

                # Step 3: Batch upload all files using upload_and_poll
                logger.debug(f"  → Uploading {len(file_tuples)} files to vector store (batch)...")

                batch_response = client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store_id,
                    files=file_tuples,
                    max_concurrency=5  # Upload up to 5 files concurrently
                )

                logger.debug(f"  ✓ Batch status: {batch_response.status}")
                logger.debug(f"  ✓ File counts: completed={batch_response.file_counts.completed}, "
                           f"failed={batch_response.file_counts.failed}, "
                           f"total={batch_response.file_counts.total}")

                # Check for failures
                if batch_response.file_counts.failed > 0:
                    logger.warning(f"  ⚠️  {batch_response.file_counts.failed} files failed to index")
                    raise APIError(f"{batch_response.file_counts.failed} out of {batch_response.file_counts.total} files failed to index")

                if batch_response.status != "completed":
                    logger.warning(f"  ⚠️  Batch processing not fully completed: {batch_response.status}")
                    raise APIError(f"Batch upload did not complete successfully: {batch_response.status}")

                # Step 4: Update vector store name with actual item count
                client.beta.vector_stores.update(
                    vector_store_id=vector_store_id,
                    name=f"{name}|{total_items}"
                )
                logger.debug(f"  ✓ Updated vector store name with item count: {total_items}")

                # Step 5: Create metadata
                metadata = VectorStoreMetadata(
                    id=str(uuid.uuid4()),
                    vector_store_id=vector_store_id,
                    name=name,
                    source_file=", ".join(source_filenames),  # Comma-separated list of filenames
                    item_count=total_items
                )

                # Add to registry
                cls._registry[metadata.id] = metadata

                # Persist to file
                await cls._save_to_file()

                logger.info(f"✅ Vector store created: {name} ({len(files)} files, {total_items} items, {vector_store_id})")
                return metadata

            except (ValueError, APIError):
                # Cleanup: delete vector store if creation failed
                if vector_store_id:
                    try:
                        logger.warning(f"  🧹 Cleaning up vector store {vector_store_id} due to error")
                        client.beta.vector_stores.delete(vector_store_id)
                        logger.debug(f"  ✓ Vector store deleted")
                    except Exception as cleanup_error:
                        logger.error(f"  ⚠️  Failed to cleanup vector store: {cleanup_error}")
                raise

        except ValueError:
            raise
        except APIError:
            raise
        except Exception as e:
            logger.error(f"❌ Failed to create vector store from multiple files: {e}", exc_info=True)
            raise APIError(f"Failed to create vector store: {e}")

    @classmethod
    def _json_to_markdown(cls, json_content: str) -> str:
        """
        Convert JSON to markdown for better semantic search.

        Formats as readable markdown with clear sections.
        """
        try:
            data = json.loads(json_content)

            # If it's a list of objects, create a formatted table
            if isinstance(data, list) and data and isinstance(data[0], dict):
                lines = ["# Dataset Items\n"]

                # Get keys from first item
                keys = list(data[0].keys())

                for idx, item in enumerate(data, 1):
                    lines.append(f"## Item {idx}")
                    for key in keys:
                        value = item.get(key, "N/A")
                        lines.append(f"- **{key}**: {value}")
                    lines.append("")

                return "\n".join(lines)
            else:
                # Fallback: just pretty-print the JSON
                return f"```json\n{json.dumps(data, indent=2)}\n```"

        except Exception as e:
            logger.warning(f"Could not convert JSON to markdown: {e}")
            # Return as-is if conversion fails
            return json_content

    @classmethod
    async def list_all(cls) -> List[VectorStoreMetadata]:
        """Get all vector stores in registry."""
        return list(cls._registry.values())

    @classmethod
    async def get_by_id(cls, store_id: str) -> Optional[VectorStoreMetadata]:
        """Get single vector store by ID."""
        return cls._registry.get(store_id)

    @classmethod
    async def delete(cls, store_id: str) -> None:
        """
        Delete vector store from registry and OpenAI.

        Args:
            store_id: Registry ID to delete

        Raises:
            ValueError: If store not found
            APIError: If OpenAI deletion fails
        """
        if store_id not in cls._registry:
            raise ValueError(f"Vector store not found: {store_id}")

        metadata = cls._registry[store_id]
        logger.info(f"🗑️  Deleting vector store: {metadata.name}")

        try:
            # Delete from OpenAI
            client = OpenAI()
            client.vector_stores.delete(metadata.vector_store_id)
            logger.debug(f"  ✓ Deleted from OpenAI: {metadata.vector_store_id}")

            # Remove from registry
            del cls._registry[store_id]
            logger.debug(f"  ✓ Removed from registry: {store_id}")

            # Persist
            await cls._save_to_file()

            logger.info(f"✅ Vector store deleted: {metadata.name}")

        except Exception as e:
            logger.error(f"❌ Failed to delete vector store: {e}", exc_info=True)
            raise APIError(f"Failed to delete vector store: {e}")

    @classmethod
    async def _save_to_file(cls) -> None:
        """Persist registry to JSON file."""
        try:
            # Create data directory if needed
            cls._registry_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to JSON-serializable format
            data = {}
            for store_id, metadata in cls._registry.items():
                data[store_id] = {
                    "id": metadata.id,
                    "vector_store_id": metadata.vector_store_id,
                    "name": metadata.name,
                    "source_file": metadata.source_file,
                    "created_at": metadata.created_at.isoformat(),
                    "item_count": metadata.item_count
                }

            # Write to file
            async with aiofiles.open(cls._registry_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2))

            logger.debug(f"💾 Registry persisted to {cls._registry_file}")

        except Exception as e:
            logger.error(f"⚠️  Failed to save registry to file: {e}")
            # Don't fail - registry is still in memory

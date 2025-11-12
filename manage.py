"""
Management utilities for RAG Backend Application
Provides CLI commands for common operations
"""
import asyncio
import sys
from sqlalchemy import select, func
from database import async_session_maker, Upload, UploadError, init_db, close_db
from qdrant_service import qdrant_service


async def list_uploads():
    """List all uploads with status counts"""
    async with async_session_maker() as db:
        # Get all uploads
        result = await db.execute(
            select(Upload).order_by(Upload.created_at.desc())
        )
        uploads = result.scalars().all()
        
        print(f"\n📊 Total Uploads: {len(uploads)}\n")
        print(f"{'ID':<6} {'Status':<12} {'Type':<20} {'Filename':<30}")
        print("=" * 80)
        
        for upload in uploads:
            print(f"{upload.id:<6} {upload.status:<12} {upload.topic:<20} {upload.file_name:<30}")
        
        # Status counts
        result = await db.execute(
            select(Upload.status, func.count(Upload.id))
            .group_by(Upload.status)
        )
        counts = dict(result.all())
        
        print("\n📈 Status Summary:")
        for status, count in counts.items():
            print(f"  {status}: {count}")


async def show_errors(upload_id: int = None):
    """Show errors for specific upload or all errors"""
    async with async_session_maker() as db:
        if upload_id:
            result = await db.execute(
                select(UploadError)
                .where(UploadError.upload_id == upload_id)
                .order_by(UploadError.created_at.desc())
            )
        else:
            result = await db.execute(
                select(UploadError)
                .order_by(UploadError.created_at.desc())
                .limit(20)
            )
        
        errors = result.scalars().all()
        
        if not errors:
            print(f"\n✅ No errors found" + (f" for upload {upload_id}" if upload_id else ""))
            return
        
        print(f"\n❌ Errors" + (f" for Upload {upload_id}" if upload_id else " (Latest 20)") + ":\n")
        
        for err in errors:
            print(f"Upload ID: {err.upload_id}")
            print(f"Stage: {err.stage}")
            print(f"Message: {err.message}")
            print(f"Time: {err.created_at}")
            print("-" * 80)


async def clear_failed():
    """Delete failed uploads and their errors"""
    async with async_session_maker() as db:
        result = await db.execute(
            select(Upload).where(Upload.status == "error")
        )
        failed = result.scalars().all()
        
        if not failed:
            print("\n✅ No failed uploads to clear")
            return
        
        print(f"\n⚠️  Found {len(failed)} failed uploads:")
        for upload in failed:
            print(f"  - {upload.id}: {upload.file_name}")
        
        confirm = input("\nDelete these uploads? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled")
            return
        
        for upload in failed:
            await db.delete(upload)
        
        await db.commit()
        print(f"✅ Deleted {len(failed)} failed uploads")


def check_qdrant():
    """Check Qdrant collection status"""
    print("\n🔍 Checking Qdrant...\n")
    
    try:
        collections = qdrant_service.client.get_collections()
        print(f"✅ Connected to Qdrant")
        print(f"Collections: {[c.name for c in collections.collections]}")
        
        # Get collection info
        from config import settings
        try:
            info = qdrant_service.client.get_collection(settings.qdrant_collection)
            print(f"\nCollection: {settings.qdrant_collection}")
            print(f"  Vectors: {info.points_count}")
            print(f"  Status: {info.status}")
        except Exception as e:
            print(f"⚠️  Collection '{settings.qdrant_collection}' not found")
    
    except Exception as e:
        print(f"❌ Qdrant error: {e}")


async def reset_status(upload_id: int, new_status: str):
    """Reset upload status (for debugging)"""
    async with async_session_maker() as db:
        result = await db.execute(
            select(Upload).where(Upload.id == upload_id)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            print(f"❌ Upload {upload_id} not found")
            return
        
        old_status = upload.status
        upload.status = new_status
        await db.commit()
        
        print(f"✅ Upload {upload_id} status: {old_status} → {new_status}")


def print_usage():
    """Print usage information"""
    print("""
RAG Backend Management Utility

Usage: python manage.py <command> [options]

Commands:
  list              List all uploads
  errors [id]       Show errors (optionally for specific upload ID)
  clear-failed      Delete all failed uploads
  check-qdrant      Check Qdrant status and collection info
  reset-status <id> <status>  Reset upload status (pending|processing|success|error)

Examples:
  python manage.py list
  python manage.py errors 5
  python manage.py clear-failed
  python manage.py check-qdrant
  python manage.py reset-status 5 pending
""")


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "list":
            await list_uploads()
        
        elif command == "errors":
            upload_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
            await show_errors(upload_id)
        
        elif command == "clear-failed":
            await clear_failed()
        
        elif command == "check-qdrant":
            check_qdrant()
        
        elif command == "reset-status":
            if len(sys.argv) < 4:
                print("❌ Usage: python manage.py reset-status <upload_id> <status>")
                return
            upload_id = int(sys.argv[2])
            status = sys.argv[3]
            if status not in ["pending", "processing", "success", "error"]:
                print("❌ Status must be: pending, processing, success, or error")
                return
            await reset_status(upload_id, status)
        
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

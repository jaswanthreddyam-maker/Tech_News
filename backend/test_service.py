import asyncio
import traceback
from app.core.database import AsyncSessionLocal
from app.ai.chat.conversation_service import ConversationService
from app.ai.chat.schemas import ConversationMode

async def main():
    try:
        async with AsyncSessionLocal() as db:
            service = ConversationService(db)
            conv_id = "test-conv-hi-debug"
            print("Starting stream_chat debug for 'hi'...")
            async for chunk in service.stream_chat(
                conversation_id=conv_id,
                message="hi",
                mode=ConversationMode.ARTICLE,
                article_id=27
            ):
                print("CHUNK:", repr(chunk))
    except Exception as e:
        print("EXCEPTION:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

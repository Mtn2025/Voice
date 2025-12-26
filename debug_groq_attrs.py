from groq import AsyncGroq
import asyncio
import os

async def main():
    try:
        client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY", "dummy"))
        print("AsyncGroq Client Attributes:")
        print(dir(client))
        try:
            print("Client.audio:", client.audio)
        except AttributeError:
            print("Client.audio: Not Found")
    except Exception as e:
        print(e)
    
if __name__ == "__main__":
    asyncio.run(main())

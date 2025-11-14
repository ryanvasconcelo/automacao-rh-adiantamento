import asyncio
from prisma import Prisma


async def main():
    db = Prisma()
    try:
        print("Conectando...")
        await db.connect()
        print("✅ Conectado com sucesso!")

        count = await db.rulemodule.count()
        print(f"RuleModules: {count}")

        await db.disconnect()
    except Exception as e:
        print(f"❌ Erro: {e}")


asyncio.run(main())

import asyncio
from openhands.metasop.router import run_metasop_for_conversation


async def main():
    await run_metasop_for_conversation("demo-conv", "demo-user", "sop: please demo", repo_root=None)


asyncio.run(main())

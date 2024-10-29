import asyncio


def run_async(func, *args, **kwargs):
    asyncio.run(func(*args, **kwargs))

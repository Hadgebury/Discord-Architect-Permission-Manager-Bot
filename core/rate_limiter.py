import asyncio
import discord
from typing import Callable, Any, List, Optional

class PacedExecutor:
    """
    Executes async tasks with controlled pacing and automatic backoff
    to respect Discord rate limits during mass operations.
    """
    def __init__(self, delay_seconds: float = 0.25):
        self.delay_seconds = delay_seconds

    async def execute_task(self, coro_func: Callable[[], Any], max_retries: int = 3) -> Any:
        for attempt in range(max_retries):
            try:
                result = await coro_func()
                if self.delay_seconds > 0:
                    await asyncio.sleep(self.delay_seconds)
                return result
            except discord.RateLimited as e:
                wait_time = getattr(e, 'retry_after', 2.0) + 0.5
                print(f"[THROTTLE] Rate limited by Discord. Backing off for {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
            except discord.HTTPException as e:
                if e.status == 429:
                    wait_time = getattr(e, 'retry_after', 2.0) + 0.5
                    print(f"[THROTTLE] HTTP 429 received. Backing off for {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
        return None

    async def execute_batch(
        self,
        items: List[Any],
        action: Callable[[Any], Any],
        progress_callback: Optional[Callable[[int, int, Any], Any]] = None
    ) -> List[Any]:
        results = []
        total = len(items)
        for idx, item in enumerate(items, start=1):
            res = await self.execute_task(lambda: action(item))
            results.append(res)
            if progress_callback:
                try:
                    cb_res = progress_callback(idx, total, item)
                    if asyncio.iscoroutine(cb_res):
                        await cb_res
                except Exception as cb_err:
                    print(f"[WARN] Progress callback warning: {cb_err}")
        return results

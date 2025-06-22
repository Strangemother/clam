
import asyncio

class Timer:
    """
    async def timeout_callback():
        await asyncio.sleep(0.1)
        print('echo!')

    print('\nfirst example:')
    timer = Timer(2, timeout_callback)  # set timer for two seconds
    await asyncio.sleep(2.5)  # wait to see timer works

    print('\nsecond example:')
    timer = Timer(2, timeout_callback)  # set timer for two seconds
    await asyncio.sleep(1)
    timer.cancel()  # cancel it
    """
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()


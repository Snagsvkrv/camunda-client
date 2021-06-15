import asyncio


def str_to_list(values):
    if isinstance(values, str):
        return [values]
    return values


def get_exception_detail(exception):
    return f"{type(exception)} : {str(exception)}"


def join(list_of_values, separator):
    if list_of_values:
        return separator.join(str(v) for v in list_of_values)
    return ""


class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.create_task(self._run())

    def reset(self):
        self._task = asyncio.create_task(self._run())

    async def _run(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()

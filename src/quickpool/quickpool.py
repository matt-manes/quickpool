import copy
import time
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable, Sequence

import printbuddies
from noiftimer import Timer
from rich.console import Console

Submission = tuple[Callable[..., Any], Sequence[Any], dict[str, Any]]


def to_args_list(args: Sequence[Any]) -> list[tuple[Any, ...]]:
    """Convert a sequence of elements to a list of tuples where each tuple contains one element from the sequence.

    Makes for easier to read calls to `quickpool` functions for the common case of single-input functions where you have a 1-dimensional sequence.

    >>> items:list[str] = foo.get_all_items()
    >>> results = for_each(bar, to_args_list(items))

    instead of

    >>> results = for_each(bar, [(item,) for item in items]))

    works with generators too:
    >>> results = for_each(bar, to_args_list(range(10)))

    instead of

    >>> results = for_each(bar, [(i,) for i in range(10)])"""
    return [(arg,) for arg in args]


def to_kwargs_list(
    kwargs: dict[Any, Any], length: int, deep_copy: bool = False
) -> list[dict[Any, Any]]:
    """
    Create a list of dictionaries from a single dictionary.

    Args:
        kwargs (dict[Any, Any]): The dictionary to make a list
        length (int): The number of copies of `kwargs`
        deep_copy (bool, optional): Whether the copies should be deep or shallow.
        When `False`, modifying one element of the returned list will modify all elements.
        Defaults to False.

    Returns:
        list[dict[Any, Any]]: A list of size `length` containing copies of `kwargs`.

    >>> kwargs = {"a": 1, "b": 2}
    >>> results = for_each(foo, kwargs_list=to_kwargs_list(kwargs, 10))

    instead of

    >>> results = for_each(foo, kwargs_list=[kwargs for _ in range(10)])
    """
    if deep_copy:
        return [copy.deepcopy(kwargs) for _ in range(length)]
    return [kwargs] * length


class _QuickPool:
    def __init__(
        self,
        functions: Sequence[Callable[..., Any]],
        args_list: Sequence[Sequence[Any]] = [],
        kwargs_list: Sequence[dict[str, Any]] = [],
        max_workers: int | None = None,
    ):
        """Quickly implement multi-threading/processing with an optional progress bar display.

        #### params

        `functions`: A list of functions to be executed.

        `args_list`: A list of tuples where each tuple consists of positional arguments to be passed to each successive function in `functions` at execution time.

        `kwargs_list`: A list of dictionaries where each dictionary consists of keyword arguments to be passed to each successive function in `functions` at execution time.

        `max_workers`: The maximum number of concurrent threads or processes. If `None`, the max available to the system will be used.

        The return values of `functions` will be returned as a list by this class' `execute` method.

        The relative ordering of `functions`, `args_list`, and `kwargs_list` matters as `args_list` and `kwargs_list` will be distributed to each function squentially.

        i.e.
        >>> for function_, args, kwargs in zip(functions, args_list, kwargs_list):
        >>>     function_(*args, **kwargs)

        If `args_list` and/or `kwargs_list` are shorter than the `functions` list, empty tuples and dictionaries will be added to them, respectively.

        e.g
        >>> import time
        >>> def dummy(seconds: int, return_val: int)->int:
        >>>     time.sleep(seconds)
        >>>     return return_val
        >>> num = 10
        >>> pool = ThreadPool([dummy]*10, [(i,) for i in range(num)], [{"return_val": i} for i in range(num)])
        >>> results = pool.execute()
        >>> print(results)
        >>> [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]"""
        self._functions = list(functions)
        self._args_list = list(args_list)
        self._kwargs_list = list(kwargs_list)
        self.max_workers = max_workers
        self._submissions: list[Submission] = []

    @property
    def executor(self) -> Any:
        raise NotImplementedError

    @property
    def workers(self) -> list[Future[Any]]:
        return self._workers

    def _get_prepared_submissions(self) -> list[Submission]:
        functions = self._functions
        args_list = self._args_list
        kwargs_list = self._kwargs_list
        num_functions = len(functions)
        num_args = len(args_list)
        num_kwargs = len(kwargs_list)
        # Pad args_list and kwargs_list if they're shorter than len(functions)
        if num_args < num_functions:
            args_list.extend([tuple() for _ in range(num_functions - num_args)])
        if num_kwargs < num_functions:
            kwargs_list.extend([dict() for _ in range(num_functions - num_kwargs)])
        return [
            (function_, args, kwargs)
            for function_, args, kwargs in zip(functions, args_list, kwargs_list)
        ]

    @property
    def submissions(self) -> list[Submission]:
        return self._submissions

    @property
    def functions(self) -> list[Callable[..., Any]]:
        return self._functions

    @property
    def args_list(self) -> list[Sequence[Any]]:
        return self._args_list

    @property
    def kwargs_list(self) -> list[dict[str, Any]]:
        return self._kwargs_list

    def get_num_workers(self) -> int:
        return len(self.workers)

    def get_finished_workers(self) -> list[Future[Any]]:
        return [worker for worker in self.workers if worker.done()]

    def get_num_finished_wokers(self) -> int:
        return len(self.get_finished_workers())

    def get_results(self) -> list[Any]:
        return [worker.result() for worker in self.workers]

    def get_unfinished_workers(self) -> list[Future[Any]]:
        return [worker for worker in self.workers if not worker.done()]

    def get_num_unfinished_workers(self) -> int:
        return len(self.get_unfinished_workers())

    def execute(
        self,
        show_progbar: bool = True,
        description: str | Callable[[], Any] = "",
        suffix: str | Callable[[], Any] = "",
    ) -> list[Any]:
        """Execute the supplied functions with their arguments, if any.

        Returns a list of function call results.

        #### params

        `show_progbar`: If `True`, print a progress bar to the terminal showing how many functions have finished executing.

        `description`: String or callable that takes no args and returns a string to display at the front of the progbar (will always include a runtime clock).

        `suffix`: String or callable that takes no args and returns a string to display after the progbar.
        """
        with self.executor as executor:
            self._submissions = self._get_prepared_submissions()
            self._workers = [
                executor.submit(submission[0], *submission[1], **submission[2])
                for submission in self.submissions
            ]
            if show_progbar:
                num_workers = self.get_num_workers()
                with printbuddies.Progress(disable=not show_progbar) as progress:
                    pool = progress.add_task(
                        f"{str(description()) if isinstance(description, Callable) else description}",
                        total=num_workers,
                        suffix=f"{str(suffix()) if isinstance(suffix, Callable) else suffix}",
                    )
                    while not progress.finished:
                        progress.update(
                            pool,
                            completed=self.get_num_finished_wokers(),
                            description=(
                                str(description())
                                if isinstance(description, Callable)
                                else description
                            ),
                            suffix=f"{str(suffix()) if isinstance(suffix, Callable) else suffix}",
                        )
                        time.sleep(0.001)
            return self.get_results()


class ProcessPool(_QuickPool):
    @property
    def executor(self) -> ProcessPoolExecutor:
        return ProcessPoolExecutor(self.max_workers)


class ThreadPool(_QuickPool):
    @property
    def executor(self) -> ThreadPoolExecutor:
        return ThreadPoolExecutor(self.max_workers)


def update_and_wait(
    function: Callable[..., Any],
    message: str | Callable[[], Any] = "",
    *args: Any,
    **kwargs: Any,
) -> Any:
    """While `function` runs with `*args` and `**kwargs`,
    print out an optional `message` (a runtime clock will be appended to `message`) at 1 second intervals.

    Returns the output of `function`.

    >>> def main():
    >>>   def trash(n1: int, n2: int) -> int:
    >>>      time.sleep(10)
    >>>      return n1 + n2
    >>>   val = update_and_wait(trash, "Waiting on trash", 10, 22)
    >>>   print(val)
    >>> main()
    >>> Waiting on trash | runtime: 9s 993ms 462us
    >>> 32"""
    spinner = "arc"
    spinner_style = "deep_pink1"
    console = Console()
    timer = Timer(subsecond_resolution=False).start()
    update_message: Callable[[], str] = (
        lambda: f"{str(message()) if isinstance(message, Callable) else message} | {timer.elapsed_str}".strip()
    )
    with console.status(
        update_message(), spinner=spinner, spinner_style=spinner_style
    ) as c:
        with ThreadPoolExecutor() as pool:
            worker = pool.submit(function, *args, **kwargs)
            while not worker.done():
                time.sleep(0.001)
                c.update(update_message())
    return worker.result()


def for_each(
    func: Callable[..., Any],
    args_list: Sequence[tuple[Any, ...]] = [],
    kwargs_list: Sequence[dict[str, Any]] = [],
    max_workers: int | None = None,
    show_progbar: bool = True,
    description: str | Callable[[], Any] = "",
    suffix: str | Callable[[], Any] = "",
    num_calls: int | None = None,
) -> list[Any]:
    """Multithread calls to `func` for each pair of `args_list` and `kwargs_list` tuples and return the results.

    #### params

    `func`: The function to execute on each pair of `args_list` and `kwargs_list` tuples.

    `args_list`: A list of tuples where each tuple consists of positional arguments to be passed to call to `func` at execution time.

    `kwargs_list`: A list of dictionaries where each dictionary consists of keyword arguments to be passed to call to `func` at execution time.

    `max_workers`: The maximum number of concurrent threads. If `None`, the max available to the system will be used.

    `show_progbar`: If `True`, print a progress bar to the terminal showing how many functions have finished executing.

    `description`: String or callable that takes no args and returns a string to display at the front of the progbar (will always include a runtime clock).

    `suffix`: String or callable that takes no args and returns a string to display after the progbar.

    `num_calls`: The number of times to call `func`. If `None` (default), `func` will be executed `max(len(args_list), len(kwargs_list))` times.

    #### e.g.
    >>> def f(t, m = 1):
    >>>     time.sleep(t * m)
    >>>     return t*m
    >>> results = for_each(f, [(i) for i in range(10)], [{"m": j*1.1} for j in range(10)])

    >>> def f():
    >>>     time.sleep(random.random())
    >>> for_each(f, num_calls=10)
    """
    funcs = [func] * (num_calls if num_calls else max(len(args_list), len(kwargs_list)))
    pool = ThreadPool(funcs, args_list, kwargs_list, max_workers)
    return pool.execute(show_progbar, description, suffix)

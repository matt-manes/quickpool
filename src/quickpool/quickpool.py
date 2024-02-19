import time
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import printbuddies
from noiftimer import Timer
from rich.console import Console


@dataclass
class Submission:
    """Class representing a submission to the executor pool.

    Consists of a function to be called as well as any arguments or keyword arguments to be passed to it.
    """

    function_: Callable[..., Any]
    args: Sequence[Any]
    kwargs: Mapping[str, Any]


class _QuickPool:
    def __init__(
        self,
        functions: list[Callable[..., Any]],
        args_list: list[tuple[Any, ...]] = [],
        kwargs_list: list[dict[str, Any]] = [],
        max_workers: int | None = None,
    ):
        """Quickly implement multi-threading/processing with an optional progress bar display.

        #### :params:

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
        self._submissions = self._prepare_submissions(functions, args_list, kwargs_list)
        self.max_workers = max_workers
        self._workers: list[Future[Any]]

    @property
    def executor(self) -> Any:
        raise NotImplementedError

    @property
    def submissions(self) -> list[Submission]:
        return self._submissions

    @property
    def workers(self) -> list[Future[Any]]:
        return self._workers

    def _prepare_submissions(
        self,
        functions: list[Callable[..., Any]],
        args_list: list[tuple[Any, ...]] = [],
        kwargs_list: list[dict[str, Any]] = [],
    ):
        num_functions = len(functions)
        num_args = len(args_list)
        num_kwargs = len(kwargs_list)
        # Pad args_list and kwargs_list if they're shorter than len(functions)
        if num_args < num_functions:
            args_list.extend([tuple() for _ in range(num_functions - num_args)])
        if num_kwargs < num_functions:
            kwargs_list.extend([dict() for _ in range(num_functions - num_kwargs)])
        return [
            Submission(function_, args, kwargs)
            for function_, args, kwargs in zip(functions, args_list, kwargs_list)
        ]

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

        #### :params:

        `show_progbar`: If `True`, print a progress bar to the terminal showing completion.

        `description`: Message to display at the front of the progress bar.
        Can be a string or a function that takes no arguments and returns an object that can be casted to a string.

        `suffix`: Message to display at the end of the progress display.
        Can be a string or a function that takes no arguments and returns an object that can be casted to a string.

        """
        with self.executor as executor:
            self._workers = [
                executor.submit(
                    submission.function_, *submission.args, **submission.kwargs
                )
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
    spinner: str = "arc",
    spinner_style: str = "deep_pink1",
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
                time.sleep(1)
                c.update(update_message())
    return worker.result()

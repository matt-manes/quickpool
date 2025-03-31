import random
import time
from typing import Any, Callable

from quickpool import quickpool


def test__get_submissions():
    def dummy(*args: Any, **kwargs: Any): ...

    num = 5
    pool = quickpool._QuickPool(  # type: ignore
        [dummy] * num, [(i, 2 * i) for i in range(5)], [{"i": i} for i in range(5)]
    )
    for i, submission in enumerate(pool.get_submissions()):
        assert submission == (dummy, (i, 2 * i), {"i": i})


def naptime(return_val: float, duration: float) -> float:
    time.sleep(duration)
    return return_val


def get_threadpool_args() -> quickpool.ThreadPool:
    num = 50
    return quickpool.ThreadPool(
        [naptime] * num, [(i, random.random() * 0.5) for i in range(num)]
    )


def get_processpool_args() -> quickpool.ProcessPool:
    num = 50
    return quickpool.ProcessPool(
        [naptime] * num, [(i, random.random() * 0.5) for i in range(num)]
    )


def get_threadpool_kwargs() -> quickpool.ThreadPool:
    num = 50
    return quickpool.ThreadPool(
        [naptime] * num,
        [],
        [{"return_val": i, "duration": random.random() * 0.5} for i in range(num)],
    )


def test__thread_pool_all_workers_args():
    pool = get_threadpool_args()
    print()
    results = pool.execute(description="test all workers args")
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


def test__thread_pool_all_workers_args_limit_workers():
    pool = get_threadpool_args()
    pool.max_workers = 1
    print()
    results = pool.execute(description="test all workers args limit workers")
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


def test__thread_pool_all_workers_args_no_bar():
    pool = get_threadpool_args()
    print()
    print("No bar display start")
    results = pool.execute(False)
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i
    print("No bar display stop")


def test__thread_pool_all_workers_kwargs():
    pool = get_threadpool_kwargs()
    print()
    results = pool.execute(description="test all workers kwargs")
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


def test__thread_pool_dynamic_prefix():
    pool = get_threadpool_args()
    pool.functions *= 10
    pool.args_list *= 10
    pool.kwargs_list *= 10
    description: Callable[[], str] = (
        lambda: f"Finished workers: {pool.get_num_finished_wokers()}|-|{pool.get_num_unfinished_workers()}"
    )
    print()
    results = pool.execute(description=description)


def test__update_and_wait():
    class Funcy:
        def __init__(self):
            self.count = 0

        def do(self) -> int:
            while self.count < 10:
                self.count += 1
                time.sleep(0.5)
            return self.count

    funcy = Funcy()
    assert (
        quickpool.update_and_wait(funcy.do, lambda: f"The count is: {funcy.count}")
        == 10
    )


def test__update_and_wait_args():
    class Funcy:
        def __init__(self):
            self.count = 0

        def do(self, count_to: int, sleep_s: float = 0.5) -> int:
            while self.count < count_to:
                self.count += 1
                time.sleep(sleep_s)
            return self.count

    funcy = Funcy()
    count_to = 10
    assert (
        quickpool.update_and_wait(
            funcy.do, lambda: f"The count is: {funcy.count}", count_to, sleep_s=0.5
        )
        == count_to
    )


def main():
    """Process pool executor requires that it be used in a "__main__" block.
    So this test needs to be run manually after installing this package as an editable install:
    >>> quickpool>pip install -e .
    >>> quickpool>"tests/test_quickpool.py" """
    pool = get_processpool_args()
    print()
    results = pool.execute()
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


if __name__ == "__main__":
    main()

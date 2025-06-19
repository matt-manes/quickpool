import random
import time
from typing import Any, Callable

from quickpool import quickpool


def test___get_prepared_submissions():
    def dummy(*args: Any, **kwargs: Any):
        ...

    num = 5
    pool = quickpool._QuickPool(  # type: ignore
        [dummy] * num, [(i, 2 * i) for i in range(5)], [{"i": i} for i in range(5)]
    )
    for i, submission in enumerate(pool._get_prepared_submissions()):  # type:ignore
        assert submission == (dummy, (i, 2 * i), {"i": i})


def naptime(return_val: float, duration: float) -> float:
    time.sleep(duration)
    return return_val


def get_threadpool_args(num: int = 50) -> quickpool.ThreadPool:
    return quickpool.ThreadPool(
        [naptime] * num, [(i, random.random() * 0.5) for i in range(num)]
    )


def get_processpool_args(num: int = 50) -> quickpool.ProcessPool:
    return quickpool.ProcessPool(
        [naptime] * num, [(i, random.random() * 0.5) for i in range(num)]
    )


def get_threadpool_kwargs(num: int = 50) -> quickpool.ThreadPool:
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
    pool = get_threadpool_args(500)
    description: Callable[
        [], str
    ] = (
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


def test__for_each_args():
    def f(t: int, m: float = 1):
        time.sleep(t * m)
        return t * m

    assert (
        len(
            quickpool.for_each(
                f, [(i,) for i in range(10)], [{"m": 0.1} for _ in range(10)]
            )
        )
        == 10
    )


def test__for_each_no_args():
    def f():
        time.sleep(0.1)
        return 0.1

    assert len(quickpool.for_each(f, num_calls=10)) == 10


def test__toargs_list():
    def f(num: int):
        time.sleep(random.random())
        return num

    results = quickpool.for_each(f, quickpool.to_args_list(range(10)))
    assert results == list(range(10))
    assert results == quickpool.for_each(f, [(i,) for i in range(10)])


def test__tokwargs_list_shallow():
    def f(num: int = 1) -> int:
        time.sleep(random.random())
        return num

    length = 10
    kwargs = {"num": 1}
    results = quickpool.for_each(
        f, kwargs_list=quickpool.to_kwargs_list(kwargs, length)
    )
    assert results == [kwargs["num"]] * length
    kwargs_list = quickpool.to_kwargs_list(kwargs, length)
    # Should change every element in list
    kwargs_list[0]["num"] = 2
    assert [kwargs_list[0]["num"]] * length == quickpool.for_each(
        f, kwargs_list=kwargs_list
    )


def test__tokwargs_list_deep():
    def f(num: int = 1) -> int:
        time.sleep(random.random())
        return num

    length = 10
    kwargs = {"num": 1}
    results = quickpool.for_each(
        f, kwargs_list=quickpool.to_kwargs_list(kwargs, length, True)
    )
    assert results == [kwargs["num"]] * length
    kwargs_list = quickpool.to_kwargs_list(kwargs, length, True)
    # Only the first element should change
    kwargs_list[0]["num"] = 2
    results = quickpool.for_each(f, kwargs_list=kwargs_list)
    assert [kwargs_list[0]["num"]] * length != results
    assert results[0] == kwargs_list[0]["num"]


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

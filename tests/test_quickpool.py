import pytest

from quickpool import quickpool
import time
import random


def test__get_submissions():
    def dummy(*args, **kwargs):
        ...

    num = 5
    pool = quickpool._QuickPool(
        [dummy] * num, [(i, 2 * i) for i in range(5)], [{"i": i} for i in range(5)]
    )
    for i, submission in enumerate(pool.submissions):
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
    results = pool.execute()
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


def test__thread_pool_all_workers_args_low_poll_rate():
    pool = get_threadpool_args()
    print()
    results = pool.execute(progbar_update_period=0.25)
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


def test__thread_pool_all_workers_args_limit_workers():
    pool = get_threadpool_args()
    pool.max_workers = 1
    print()
    results = pool.execute()
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


def test__thread_pool_all_workers_args_no_bar():
    pool = get_threadpool_args()
    print()
    results = pool.execute(False)
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


def test__thread_pool_all_workers_kwargs():
    pool = get_threadpool_kwargs()
    print()
    results = pool.execute()
    for i, result in zip(range(len(pool.functions)), results):
        assert result == i


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

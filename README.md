# quickpool

Use ProcessPoolExecutor and ThreadPoolExecutor from concurrent.futures with a progress bar and less boilerplate.

## Installation

Install with:

<pre>
pip install quickpool
</pre>

## Usage

<pre>
>>> import random
>>> import time
>>> import quickpool
>>> def naptime(base_duration: float, multiplier: float, return_val: int)->int:
...   time.sleep(base_duration * multiplier)
...   return return_val
...
>>> def demo():
...   iterations = 25
...   pool = quickpool.ThreadPool(
...   functions = [naptime] * iterations,
...   args_list = [(random.random() * 5, random.random()) for _ in range(iterations)],
...   kwargs_list = [{"return_val": i} for i in range(iterations)])
...   results = pool.execute()
...   print(results)
...
>>> demo()
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 3s
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
</pre>

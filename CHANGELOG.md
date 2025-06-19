# Changelog

## v2.2.0 (2025-06-19)

#### New Features

* add `to_kwargs_list()` convenience function

## v2.1.0 (2025-05-15)

#### New Features

* implement `to_args_list()`
* implement `for_each()`

## v2.0.0 (2025-03-31)

#### New Features

* BREAKING remove `spinner` and `spinner_style` args from `update_and_wait`

#### Others

* update formatting
* format changelog

## v1.0.2 (2024-02-20)

#### Fixes

* Revert `Submission` dataclass implementation due to threading issues

## v1.0.1 (2024-02-19)

#### Refactorings

* `update_and_wait` implements a rich status object

## v1.0.0 (2024-02-17)

#### Refactorings

* implement `Submission` dataclass
* improve type annotation coverage
* BREAKING change progress bar implementation and remove irrelevant args to `execute()`

## v0.1.1 (2023-11-17)

#### Others

* add update_and_wait to __init__.py

## v0.1.0 (2023-11-17)

#### New Features

* add update_and_wait function

#### Performance improvements

* add parameters to execute for providing prefixes and suffixes to execute()

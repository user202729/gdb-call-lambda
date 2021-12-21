# gdb-call-lambda
Call C++ lambda functions from gdb.

## Install

* Install the Python package in somewhere Python can see.
* In .gdbinit add:

```
python import gdb_call_lambda
```

## Usage

Call a lambda like `printl f(x)`, where the `f` is the lambda.

I.e., call as usual, just replace `print` with `printl`.

The lambda expression (`f` in this case) must not have any `(` characters.

## How it works internally/what to do if it doesn't work

See post https://stackoverflow.com/a/70254108/5267751.

There's a known bug where gdb/tools can't demangle a symbol that gcc generates, see `B` in test.


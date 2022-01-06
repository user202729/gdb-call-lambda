# not to be run directly. Run test.sh instead.

import gdb_call_lambda
for func, args in [
		("a", "5"),
		("a2", "5"),
		("a3", "5"),
		("a4", "5"),
		("b", "b, 5"),
		("A", "5"),
		("A2", "5"),
		("B", "B, 5"),
		]:
    try:
        print(gdb_call_lambda.command.invoke(f"{func}({args})", False))
        print("success", func, args)
    except:
        print("error  ", func, args)

    try:
        print(gdb_call_lambda.func.invoke(
			gdb.parse_and_eval(func),
			*[gdb.parse_and_eval(arg) for arg in args.split(",")]
			, False))
        gdb.execute(f"print $calll({func}, {args})")
        print("func success", func, args)
    except:
        print("func error  ", func, args)


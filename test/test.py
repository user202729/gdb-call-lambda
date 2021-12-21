# not to be run directly. Run test.sh instead.

import gdb_call_lambda
for statement in ["a(5)", "a2(5)", "a3(5)", "b(b, 5)", "A(5)", "B(B, 5)"]:
    try:
        print(gdb_call_lambda.call_lambda_command.invoke(statement, False))
        print("success", statement)
    except:
        print("error  ", statement)


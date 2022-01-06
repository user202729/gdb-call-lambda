# vim: set et sts=4:

import typing
from typing import TypeVar, Optional
from typing import Callable
import functools
from dataclasses import dataclass
import traceback
import ast
import subprocess
import re


import gdb  # type: ignore


"""
to reload:
python import imp; import gdb_call_lambda; imp.reload(gdb_call_lambda)
import imp; import gdb_call_lambda; imp.reload(gdb_call_lambda)
"""

T=TypeVar("T")

def assert_not_none(x: Optional[T])->T:
    assert x is not None
    return x

def extract_target_type(lambda_symbol: str)->str:
    ## NOTE, use gdb `maintenance print type` command, not Python API, may be fragile
    return assert_not_none(re.match(
        r""".*
code 0x7 \(TYPE_CODE_FUNC\).*?
nfields.*?
  \[0\].*?
    code 0x1 \(TYPE_CODE_PTR\).*?
    target_type (\S+)""",
        gdb.execute(f"maintenance print type '{lambda_symbol}'", to_string=True),
        re.DOTALL
        ))[1]

def extract_type_identifier(expression: str)->list[str]:
    # return both the type_chain and the type node data (sometimes one is used and sometimes the other...???)
    e=gdb.execute("maintenance print type " + expression, to_string=True)
    try:
        if re.match(
                r""".*?
code 0x12 \(TYPE_CODE_REF\)
""", e, re.DOTALL):
            # the expression is considered to have a reference type by gdb. Need to get the underlying struct
            return [assert_not_none(re.match(
                    r""".*?
target_type (\S+)
"""
                    , e, re.DOTALL))[1]]
        else:
            # the expression is considered to have a struct type by gdb
            assert re.match(
                r""".*?
code 0x3 \(TYPE_CODE_STRUCT\)
""", e, re.DOTALL)
            return [
                    assert_not_none(re.match(
                    r""".*?
type_chain (\S+)
""",
                    e, re.DOTALL
                    ))[1],
                        assert_not_none(re.match(
                    r"""type node (\S+)""",
                    e, re.DOTALL
                    ))[1],
                    ]

    except:
        open("/tmp/aa", "w").write(e)
        raise



F=TypeVar("F", bound=Callable)
def wrap_print_exception_on_error(f: F)->F:
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            traceback.print_exc()
            raise
    return typing.cast(F, wrap)

@dataclass
class CallLambda(gdb.Command):
    executable_object_file=None
    lambda_symbol: Optional[dict[str, str]]=None

    def __init__(self)->None:
        super().__init__("printl", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION)

    def get_lambda_call_operator(self, lambda_expression: str)->str:
        """
        Given a string of a gdb expression whose value is a lambda,
        return the name of the symbol of the operator() of that lambda.

        Example:
        self.get_lambda_call_operator("a") = "main::{lambda(int)#1}::operator()(int) const"

        To be used in gdb expressions, single quotes around the expression are usually required.
        """
        self.recompute_symbols()
        lambda_symbol=assert_not_none(self.lambda_symbol)
        result={
                y
                for x in extract_type_identifier(lambda_expression)
                for y in [lambda_symbol.get(x)]
                if y
                }
        assert len(result)==1, f"Found {len(result)} instead of 1 possible candidates"
        return result.pop()

    def get_lambda_call_operator_wrapped(self, lambda_expression: str)->str:
        """
        same as above, but always return '$calllambda_lambdacalloperator'.

        The result can only be used once before another invocation of this function.

        Used to workaround a gdb bug (at the time of writing)

        gdb.set_convenience_variable("a",
            gdb.parse_and_eval( "'main::{lambda(int)#1}::operator()( int) const'" )
            )
        → null
        """
        result="$calllambda_lambdacalloperator"
        gdb.execute(f"set {result}='{self.get_lambda_call_operator(lambda_expression)}'")
        return result

    def get_gdb_expression(self, lambda_expression: str, lambda_arguments: str)->str:
        """
        Return a string of a gdb expression, that when evaluated (with gdb.parse_and_eval or
        gdb 'print' command for example), results in the value of the lambda function call.

        The result can only be used once before another invocation of this function.
        (depends on the convenience variable '$calllambda_lambdacalloperator')
        """
        lambda_arguments=lambda_arguments.strip()
        lambda_expression=lambda_expression.strip()
        assert lambda_expression


        lambda_call_operator=self.get_lambda_call_operator_wrapped(lambda_expression)
        return (lambda_call_operator + "(" +
                "&(" + lambda_expression + ")" +
                ("," if lambda_arguments else "") +
                lambda_arguments
                + ")")

    @wrap_print_exception_on_error
    def invoke(self, argument: str, from_tty: bool)->None:
        argument=argument.strip()
        assert argument.endswith(")") and "(" in argument, "Argument should have the form func(arg, arg)"
        argument=argument[:-1]
        lambda_expression, lambda_arguments=argument.split("(", maxsplit=1)
        gdb.execute("print "+self.get_gdb_expression(lambda_expression, lambda_arguments))

    def recompute_symbols(self, current_object_file=None)->None:
        if current_object_file is None:
            current_object_file=gdb.objfiles()[0]
        if self.executable_object_file==current_object_file:
            return
        self.executable_object_file=current_object_file

        executable_file_name=current_object_file.filename

        ## ======== step 2: get the symbols (functions) in the executable -- NOTE use the external executable `nm`
        all_symbols=[
                line.split(' ', maxsplit=2)[2]
                for line in subprocess.check_output(["nm", "--demangle", executable_file_name]).decode('u8').splitlines()
                ]

        ## ======== step 3: filter, keep only the interesting ones and compute target_type
        self.lambda_symbol={
                extract_target_type(symbol): symbol
                for symbol in all_symbols
                if "{lambda" in symbol and "operator()" in symbol
                }

command=CallLambda()


class CallLambdaFunction(gdb.Function):
    @wrap_print_exception_on_error
    def invoke(self, *args):
        assert len(args)>=1, "Must provide the lambda as first argument"
        lambda_object=args[0]
        gdb.set_convenience_variable("calllambda_lambdaobject", lambda_object)
        return gdb.parse_and_eval(
                "'" + command.get_lambda_call_operator("$calllambda_lambdaobject") + "'"
                )(*args)

func=CallLambdaFunction("calll")

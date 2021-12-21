# vim: set et sts=4:

from typing import TypeVar, Optional
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

def extract_type_identifier(expression: str)->str:
    e=gdb.execute("maintenance print type " + expression, to_string=True)
    try:
        if re.match(
                r""".*?
code 0x12 \(TYPE_CODE_REF\)
""", e, re.DOTALL):
            # the expression is considered to have a reference type by gdb. Need to get the underlying struct
            return assert_not_none(re.match(
                    r""".*?
target_type (\S+)
"""
                    , e, re.DOTALL))[1]
        else:
            # the expression is considered to have a struct type by gdb
            assert re.match(
                r""".*?
code 0x3 \(TYPE_CODE_STRUCT\)
""", e, re.DOTALL)
            return assert_not_none(re.match(
                #r"""type node (\S+)""",
                r""".*?
type_chain (\S+)
""",
                e, re.DOTALL
                ))[1]

    except:
        open("/tmp/aa", "w").write(e)
        raise


@dataclass
class CallLambda(gdb.Command):
    executable_object_file=None
    lambda_symbol: Optional[dict[str, str]]=None

    def __init__(self)->None:
        super().__init__("printl", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION)

    def invoke(self, argument: str, from_tty: bool)->None:
        try:
            argument=argument.strip()
            assert argument.endswith(")") and "(" in argument, "Argument should have the form func(arg, arg)"
            argument=argument[:-1]
            lambda_expression, lambda_arguments=argument.split("(", maxsplit=1)
            lambda_arguments=lambda_arguments.strip()

            current_object_file=gdb.objfiles()[0]
            if self.executable_object_file != current_object_file:
                self.recompute_symbols(current_object_file)

            lambda_call_operator=assert_not_none(self.lambda_symbol)[extract_type_identifier(lambda_expression)]

            #gdb.set_convenience_variable("calllambda_lambdacalloperator",
            #       gdb.parse_and_eval("'" + lambda_call_operator + "'")
            #       )

            gdb.execute("set $calllambda_lambdacalloperator='" + lambda_call_operator + "'")
            
            #gdb.set_convenience_variable("a", gdb.parse_and_eval( "'main::{lambda(int)#1}::operator()( int) const'" ))
            # → null!? GDB bug......

            gdb.execute("print $calllambda_lambdacalloperator(" + 
                    "&(" + lambda_expression + ")" +
                    ("," if lambda_arguments else "") +
                    lambda_arguments
                    + ")")
        except:
            #traceback.print_exc()
            raise

    def recompute_symbols(self, current_object_file=None)->None:
        if current_object_file is None:
            current_object_file=gdb.objfiles()[0]
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

call_lambda_command=CallLambda()

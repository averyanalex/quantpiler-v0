from quantpiler import compiler
from quantpiler import utils

from qiskit.circuit.quantumregister import Qubit, AncillaQubit
from qiskit import QuantumRegister, ClassicalRegister
from qiskit.circuit import QuantumCircuit

import ast


def test_get_args_vars():
    def some_func(a: 1, b: 3, c: 8, d: 5):
        pass

    args = compiler.get_args_vars(some_func)
    assert args == {"a": 1, "b": 3, "c": 8, "d": 5}


def test_get_used_vars():
    st = "d | ~(a ^ b + c) & c"
    st_ast = ast.parse(st, mode="single").body[0].value
    used_vars = compiler.get_used_vars(st_ast)
    assert used_vars == ["d", "a", "b", "c", "c"]


def test_assemble_xor():
    a = QuantumRegister(4)
    b = QuantumRegister(4)
    c = QuantumRegister(4)
    c_cl = ClassicalRegister(4)
    qc = QuantumCircuit(a, b, c, c_cl)

    qc.x(a[1])
    qc.x(a[3])
    qc.x(b[2])
    qc.x(b[3])

    comp = compiler.Compiler()
    comp.set_qc(qc)
    comp.assemble_xor([a, b], c)

    qc.measure(c, c_cl)

    res = utils.execute_qc_once(qc)
    assert res[-4:] == '0110'

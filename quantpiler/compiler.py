"""
Python -> QuantumCircuit compiler.
"""

from typing import Callable, List

import dis

from qiskit.circuit.quantumregister import Qubit, AncillaQubit
from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit

from .qops import (
    QueuedAnd,
    QueuedBool,
    QueuedEqual,
    QueuedNot,
    QueuedNotEqual,
    QueuedOp,
    QueuedOr,
    QueuedRegister,
)


def assemble(func: Callable, ancillas_count: int) -> QuantumCircuit:
    """Compile python function to qiskit circuit.

    Args:
        func (Callable): Function to compile.
        ancillas_count (int): Number of needed ancilla qubits.

    Raises:
        NotImplementedError: Some of required operations not supported yet.

    Returns:
        QuantumCircuit: Compiled circuit.
    """

    input_vars = {}
    tmp_vars = {}
    all_vars = {}

    input_args_count = func.__code__.co_argcount
    varnames = func.__code__.co_varnames

    for i in range(len(varnames)):
        name = varnames[i]
        if i < input_args_count:
            input_vars[name] = QuantumRegister(1, name=name)
        else:
            tmp_vars[name] = AncillaRegister(1, name=name)

    all_vars = input_vars | tmp_vars

    anc: List[AncillaQubit] = []
    for i in range(ancillas_count):
        anc.append(AncillaQubit())
    ancillas_qr = AncillaRegister(bits=anc)

    qc = QuantumCircuit(
        *input_vars.values(), *tmp_vars.values(), ancillas_qr, name=func.__name__
    )

    ops_stack: List[QueuedOp] = []

    bcode = dis.Bytecode(func)
    for inst in bcode:
        opn = inst.opname

        if opn == "LOAD_FAST":
            target = all_vars[inst.argval]
            ops_stack.append(QueuedRegister(qc, anc, target))

        elif opn == "LOAD_CONST":
            const = inst.argval
            ops_stack.append(QueuedBool(qc, anc, const))

        elif opn == "STORE_FAST":
            op = ops_stack.pop()
            target = all_vars[inst.argval]
            op.execute(target)

        elif opn == "BINARY_OR":
            a = ops_stack.pop()
            b = ops_stack.pop()
            ops_stack.append(QueuedOr(qc, anc, a, b))

        elif opn == "UNARY_NOT":
            a = ops_stack.pop()
            ops_stack.append(QueuedNot(qc, anc, a))

        elif opn == "BINARY_AND":
            a = ops_stack.pop()
            b = ops_stack.pop()
            ops_stack.append(QueuedAnd(qc, anc, a, b))

        elif opn == "COMPARE_OP":
            optype = inst.argval
            if optype == "!=":
                a = ops_stack.pop()
                b = ops_stack.pop()
                ops_stack.append(QueuedNotEqual(qc, anc, a, b))
            elif optype == "==":
                a = ops_stack.pop()
                b = ops_stack.pop()
                ops_stack.append(QueuedEqual(qc, anc, a, b))
            else:
                raise NotImplementedError(
                    f"{inst.argval} comparison not implemented yet"
                )

        elif opn == "RETURN_VALUE":
            pass

        else:
            raise NotImplementedError(f"Operation {inst.opname} not implemented yet")

    return qc

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
    QueuedQubit,
)


def compile(func: Callable, ancillas_count: int) -> QuantumCircuit:
    """Compile python function to qiskit circuit.

    Args:
        func (Callable): Function to compile.
        ancillas_count (int): Number of needed ancilla qubits.

    Raises:
        NotImplementedError: Some of required operations not supported yet.

    Returns:
        QuantumCircuit: Compiled circuit.
    """

    input_qubits = {}
    tmp_qubits = {}
    all_qubits = {}

    input_args_count = func.__code__.co_argcount
    varnames = func.__code__.co_varnames

    for i in range(len(varnames)):
        name = varnames[i]
        if i < input_args_count:
            input_qubits[name] = Qubit()
        else:
            tmp_qubits[name] = Qubit()

    all_qubits = input_qubits | tmp_qubits

    input_qr = QuantumRegister(bits=list(input_qubits.values()))
    tmp_qr = QuantumRegister(bits=list(tmp_qubits.values()))

    anc: [AncillaQubit] = []
    for i in range(ancillas_count):
        anc.append(AncillaQubit())

    ancilla_qr = AncillaRegister(bits=anc)

    qc = QuantumCircuit(input_qr, tmp_qr, ancilla_qr, name=func.__name__)

    stack: List[QueuedOp] = []

    bc = dis.Bytecode(func)
    for inst in bc:
        opname = inst.opname

        if opname == "LOAD_FAST":
            target = all_qubits[inst.argval]
            stack.append(QueuedQubit(qc, anc, target))

        elif opname == "LOAD_CONST":
            const = inst.argval
            stack.append(QueuedBool(qc, anc, const))

        elif opname == "STORE_FAST":
            op = stack.pop()
            target = all_qubits[inst.argval]
            op.execute(target)

        elif opname == "BINARY_OR":
            a = stack.pop()
            b = stack.pop()
            stack.append(QueuedOr(qc, anc, a, b))

        elif opname == "UNARY_NOT":
            a = stack.pop()
            stack.append(QueuedNot(qc, anc, a))

        elif opname == "BINARY_AND":
            a = stack.pop()
            b = stack.pop()
            stack.append(QueuedAnd(qc, anc, a, b))

        elif opname == "COMPARE_OP":
            optype = inst.argval
            if optype == "!=":
                a = stack.pop()
                b = stack.pop()
                stack.append(QueuedNotEqual(qc, anc, a, b))
            elif optype == "==":
                a = stack.pop()
                b = stack.pop()
                stack.append(QueuedEqual(qc, anc, a, b))
            else:
                raise NotImplementedError(
                    f"{inst.argval} comparison not implemented yet"
                )

        elif opname == "RETURN_VALUE":
            pass

        else:
            raise NotImplementedError(f"Operation {inst.opname} not implemented yet")

    return qc

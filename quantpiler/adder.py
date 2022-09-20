"""
Quantum adder circuit generator.
"""

from typing import Union, List, Dict

from qiskit import QuantumRegister
from qiskit.circuit import QuantumCircuit


def new_adder(size: int) -> QuantumCircuit:
    """Generate adder circuit.

    Args:
        size (int): Number of bits.

    Returns:
        QuantumCircuit: Generated adder.
    """

    a = QuantumRegister(size, name="a")
    b = QuantumRegister(size, name="b")
    sm = QuantumRegister(size, name="sum")

    qc = QuantumCircuit(a, b, sm, name="adder")

    for i in range(size - 1):
        qc.ccx(a[i], b[i], sm[i + 1])
        qc.cx(a[i], b[i])
        qc.ccx(b[i], sm[i], sm[i + 1])
        qc.cx(b[i], sm[i])
        qc.cx(a[i], b[i])
        qc.barrier()

    qc.cx(a[size - 1], sm[size - 1])
    qc.cx(b[size - 1], sm[size - 1])

    return qc

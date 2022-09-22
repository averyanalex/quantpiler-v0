"""
Quantum adder circuit generator.
"""

from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit


def new_full_adder() -> QuantumCircuit:
    """Generate full adder circuit.

    Returns:
        QuantumCircuit: Full adder circuit.
    """
    a = QuantumRegister(1, name="a")
    b = QuantumRegister(1, name="b")
    sm = QuantumRegister(1, name="sum")
    c = QuantumRegister(1, name="cout")

    qc = QuantumCircuit(a, b, sm, c, name="full_adder")

    qc.ccx(a, b, c)
    qc.cx(a, b)
    qc.ccx(b, sm, c)
    qc.cx(b, sm)
    qc.cx(a, b)

    return qc


def new_inplace_full_adder() -> QuantumCircuit:
    a = QuantumRegister(1, name="a")
    b = QuantumRegister(1, name="b")
    c = QuantumRegister(1, name="c")
    anc = AncillaRegister(1)

    qc = QuantumCircuit(a, b, c, anc, name="inplace_full_adder")

    qc.ccx(a, b, anc)
    qc.cx(a, b)
    qc.ccx(b, c, anc)
    qc.cx(b, c)
    qc.cx(a, b)
    qc.swap(b, c)
    qc.swap(c, anc)

    return qc


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
    full_adder = new_full_adder()

    for i in range(size - 1):
        qc.compose(full_adder, qubits=[a[i], b[i], sm[i], sm[i + 1]], inplace=True)

    qc.cx(a[size - 1], sm[size - 1])
    qc.cx(b[size - 1], sm[size - 1])

    return qc

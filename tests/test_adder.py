from quantpiler.adder import new_adder

from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit

from quantpiler.utils import execute_qc_once


def test_adder():
    a = QuantumRegister(6, name="a")
    b = QuantumRegister(6, name="b")
    sm = QuantumRegister(6, name="sum")
    qc = QuantumCircuit(a, b, sm, name="test_adder")

    for i in (2, 3, 4):
        qc.x(a[i])

    for i in (1, 2, 4):
        qc.x(b[i])

    adder = new_adder(6)
    qc.compose(adder, inplace=True)

    result = execute_qc_once(qc)
    assert result == "110010010110011100"

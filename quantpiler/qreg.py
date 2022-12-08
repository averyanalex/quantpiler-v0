from qiskit import QuantumRegister, QuantumCircuit


class QReg(QuantumRegister):
    tp: str = "int"
    tmp: bool = False
    qc: QuantumCircuit = None

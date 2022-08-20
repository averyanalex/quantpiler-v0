from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit


def new_oracle_checker(expected_data: [bool]):
    data = QuantumRegister(len(expected_data), name="data")
    anc = AncillaRegister(1)
    result = QuantumRegister(1, name="result")
    qc = QuantumCircuit(data, result, anc, name="oracle_checker")

    for i in range(len(expected_data)):
        if not expected_data[i]:
            qc.x(data[i])

    qc.mcx(data, anc)
    qc.cz(anc, result)

    for i in range(len(expected_data)):
        if not expected_data[i]:
            qc.x(data[i])

    return qc

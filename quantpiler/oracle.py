from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit


def new_oracle_checker(expected_data: [bool]):
    data = QuantumRegister(len(expected_data), name="data")
    result = QuantumRegister(1, name="result")
    qc = QuantumCircuit(data, result, name="oracle_checker")

    for i in range(len(expected_data)):
        if not expected_data[i]:
            qc.x(data[i])

    qc.h(result)
    qc.mcx(data, result)
    qc.h(result)

    for i in range(len(expected_data)):
        if not expected_data[i]:
            qc.x(data[i])

    return qc

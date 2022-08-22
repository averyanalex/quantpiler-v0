"""
Some circuits useful for quantum oracles.
"""

from typing import List

from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit


def new_oracle_checker(expected_data: List[bool]) -> QuantumCircuit:
    """Generate data checker for quantum oracles.

    This circuit will flip phase of `result` (last) qubit only if all of the `data` qubits equals to `expected_data`.

    Args:
        expected_data (List[bool]): List of expected bits on `data` qubits.

    Returns:
        QuantumCircuit: The newly generated oracle-checker circuit.
    """

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

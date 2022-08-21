"""
Quantum-RAM circuit generator.
"""

from typing import Union, List, Dict

from qiskit import QuantumRegister
from qiskit.circuit import QuantumCircuit


def new_qram(address_count: int, data_count: int, values: Union[Dict[int, int], List[int]]) -> QuantumCircuit:
    """
    Generate qRAM circuit.

    Parameters
    ----------
    address_count : int
        Number of address qubits
    data_count : int
        Number of data qubits
    values : Union[Dict[int, int], List[int]]
        Saved qRAM data

    Returns
    -------
    QuantumCircuit
        The newly generated qRAM circuit

    Raises
    ------
    ValueError
        Some address/data in values is larger than maximum for address/data qubits count
    """

    address = QuantumRegister(address_count, name="addr")
    data = QuantumRegister(data_count, name="data")
    qc = QuantumCircuit(address, data, name="qram")

    if type(values) is list:
        values_dict = {}
        for i in range(len(values)):
            values_dict[i] = values[i]
        values = values_dict

    key_i = 0
    for key in values:
        key_i = key_i + 1

        if key > 2**address_count - 1:
            raise ValueError(
                f"Key {key} larger than maximum ({2**address_count - 1})")

        if key > 2**address_count - 1:
            raise ValueError(
                f"Value {values[key]} larger than maximum ({2**data_count - 1})")

        k = [(key >> bit) & 1 for bit in range(address_count - 1, -1, -1)]
        v = [(values[key] >> bit) & 1 for bit in range(data_count - 1, -1, -1)]

        for i in range(address_count):
            if not k[i]:
                qc.x(address[i])

        for i in range(data_count):
            if v[i]:
                qc.mcx(address, data[i])

        for i in range(address_count):
            if not k[i]:
                qc.x(address[i])

        if key_i != len(values):
            qc.barrier()

    return qc

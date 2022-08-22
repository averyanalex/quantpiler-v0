"""
Some useful utilites.
"""

from typing import List, Union

from math import log2, ceil

from qiskit import BasicAer, execute
from qiskit.circuit import QuantumCircuit


def int_to_bits(number: int, bits=None) -> List[bool]:
    """Convert integer to list of bits.

    Args:
        number (int): Number to convert.
        bits (int, optional): Number of bits. Defaults to number's bits.

    Returns:
        List[bool]: Resulting list of bits.
    """
    if not bits:
        bits = ceil(log2(number))

    return [(number >> bit) & 1 for bit in range(bits - 1, -1, -1)]


def execute_qc_once(qc: QuantumCircuit, measure=True) -> List[bool]:
    """Execute circuit once and return result.

    Args:
        qc (QuantumCircuit): Circuit to execute.
        measure (bool, optional): Run qc.measure_all() before executing. Defaults to True.

    Returns:
        List[bool]: Execution result.
    """
    m_qc = qc.copy()
    if measure:
        m_qc.measure_all()

    qasm_sim = BasicAer.get_backend("qasm_simulator")
    result = execute(m_qc, backend=qasm_sim, shots=1).result()

    answer = result.get_counts()
    bits = list(answer.keys())[0]

    return bits

"""
Some useful utilites.
"""

from typing import List, Dict, Union, Callable

from math import log2, ceil

from qiskit import BasicAer, execute
from qiskit.circuit import QuantumCircuit, ClassicalRegister

from . import compiler


def int_to_bits(number: int, bits=None) -> List[bool]:
    """Convert signed integer to list of bits.

    Args:
        number (int): Number to convert.
        bits (int, optional): Number of bits. Defaults to number's bits.

    Returns:
        List[bool]: Resulting list of bits.
    """
    if not bits:
        bits = get_int_len(number)

    if get_int_len(number) > bits:
        raise NotImplementedError()

    return [(number >> bit) & 1 for bit in range(bits - 1, -1, -1)]


def uint_to_bits(number: int, bits=None) -> List[bool]:
    """Convert unsigned integer to list of bits.

    Args:
        number (int): Number to convert.
        bits (int, optional): Number of bits. Defaults to number's bits.

    Returns:
        List[bool]: Resulting list of bits.
    """
    if not bits:
        bits = get_uint_len(number)

    if number > 2**bits - 1:
        raise NotImplementedError()

    if number < 0:
        raise NotImplementedError()

    return [(number >> bit) & 1 for bit in range(bits - 1, -1, -1)]


def get_int_len(number: int) -> int:
    return number.bit_length() + 1


def get_uint_len(number: int) -> int:
    return number.bit_length()


def bits_to_int(bitlist: List[bool]) -> int:
    res = 0

    for ele in bitlist[1:]:
        res = (res << 1) | ele

    if bitlist[0]:
        return res - 2 ** (len(bitlist) - 1)
    else:
        return res


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


def compile_execute(func: Callable, args: Dict[str, int] = {}) -> Union[None, int]:
    comp = compiler.Compiler()
    comp.assemble(func)

    qc = comp.get_qc()
    ret = comp.get_ret()
    ret_cl = ClassicalRegister(len(ret))

    qc.add_register(ret_cl)
    qc.measure(ret, ret_cl)

    qasm_sim = BasicAer.get_backend("qasm_simulator")
    result = execute(qc, backend=qasm_sim, shots=1).result()
    answer = list(result.get_counts().keys())[0]

    return answer

from quantpiler import qram

from qiskit import QuantumRegister, ClassicalRegister
from qiskit.circuit import QuantumCircuit

from quantpiler.utils import int_to_bits, execute_qc_once


def check_qram(qram, addr, data):
    aqr = QuantumRegister(2)
    dqr = QuantumRegister(3)
    rqr = ClassicalRegister(3)

    qc = QuantumCircuit(aqr, dqr, rqr)

    k = int_to_bits(addr, 2)
    v = int_to_bits(data, 3)

    for i in range(2):
        if k[i]:
            qc.x(aqr[i])
    qc.barrier()

    qc.compose(qram, qubits=[0, 1, 2, 3, 4], inplace=True)
    qc.barrier()
    qc.measure(dqr, rqr)

    bits = execute_qc_once(qc, measure=False)

    v_str = ""
    for v_b in v:
        v_str = v_str + str(v_b)

    assert bits[::-1] == v_str


def test_qram_dict():
    values = {0: 1, 1: 3, 2: 6, 3: 7}
    ram = qram.new_qram(2, 3, values)

    for addr in values:
        data = values[addr]

        check_qram(ram, addr, data)


def test_qram_list():
    values = [1, 3, 6, 7]
    ram = qram.new_qram(2, 3, values)

    for addr in range(len(values)):
        data = values[addr]

        check_qram(ram, addr, data)

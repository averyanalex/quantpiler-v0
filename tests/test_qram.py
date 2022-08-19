from quantpiler import qram

from qiskit import QuantumRegister, ClassicalRegister
from qiskit.circuit import QuantumCircuit
from qiskit import BasicAer, execute

qasm_sim = BasicAer.get_backend('qasm_simulator')


def test_qram():
    values = {0: 1, 1: 3, 2: 6, 3: 7}
    ram = qram.new_qram(2, 3, values)

    for key in values:
        aqr = QuantumRegister(2)
        dqr = QuantumRegister(3)
        rqr = ClassicalRegister(3)

        qc = QuantumCircuit(aqr, dqr, rqr)

        k = [(key >> bit) & 1 for bit in range(2 - 1, -1, -1)]
        v = [(values[key] >> bit) & 1 for bit in range(3 - 1, -1, -1)]

        for i in range(2):
            if k[i]:
                qc.x(aqr[i])
        qc.barrier()

        qc.compose(ram, qubits=[0, 1, 2, 3, 4], inplace=True)
        qc.barrier()
        qc.measure(dqr, rqr)

        print(qc.draw())

        results = execute(qc, backend=qasm_sim, shots=1).result()
        answer = results.get_counts()
        bits = list(answer.keys())[0]

        v_str = ''
        for v_b in v:
            v_str = v_str + str(v_b)

        assert bits[::-1] == v_str

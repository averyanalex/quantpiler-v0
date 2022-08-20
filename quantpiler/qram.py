from qiskit import QuantumRegister
from qiskit.circuit import QuantumCircuit


def new_qram(address_count: int, data_count: int, values):
    address = QuantumRegister(address_count, name="addr")
    data = QuantumRegister(data_count, name="data")
    qc = QuantumCircuit(address, data, name="qram")

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

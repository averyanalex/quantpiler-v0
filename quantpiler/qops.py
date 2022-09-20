from typing import List

from qiskit.circuit.quantumregister import QuantumRegister, AncillaQubit
from qiskit.circuit import QuantumCircuit


class QueuedOp:
    qc: QuantumCircuit
    anc: List[AncillaQubit]
    result_anc: AncillaQubit

    def is_qubit(self) -> bool:
        return False

    def execute(self, target: QuantumRegister):
        raise NotImplementedError()

    def prepare_anc(self):
        self.result_anc = self.anc.pop()
        self.execute(self.result_anc)
        return self.result_anc

    def drop_anc(self):
        self.anc.append(self.result_anc)


class QueuedRegister(QueuedOp):
    value: QuantumRegister

    def __init__(
        self, qc: QuantumCircuit, anc: List[AncillaQubit], value: QuantumRegister
    ):
        self.qc = qc
        self.anc = anc
        self.value = value

    def is_qubit(self) -> bool:
        return True

    def execute(self, target: QuantumRegister):
        # print(f"{target} = {self.value}")
        self.qc.reset(target)
        self.qc.cx(self.value, target)

    def prepare_anc(self):
        return self.value

    def drop_anc(self):
        pass


class QueuedBool(QueuedOp):
    value: bool

    def __init__(self, qc: QuantumCircuit, anc: List[AncillaQubit], value: bool):
        self.qc = qc
        self.anc = anc
        self.value = value

    def execute(self, target: QuantumRegister):
        # print(f"{target} = {self.value}")
        self.qc.reset(target)
        if self.value:
            self.qc.x(target)


class QueuedNot(QueuedOp):
    a: QueuedOp

    def __init__(self, qc: QuantumCircuit, anc: List[AncillaQubit], a: QueuedOp):
        self.qc = qc
        self.anc = anc
        self.a = a

    def execute(self, target: QuantumRegister):
        # print(f"{target} = not {self.a}")

        a1 = self.a.prepare_anc()

        # target = True
        self.qc.reset(target)
        self.qc.x(target)

        self.qc.cx(a1, target)

        self.a.drop_anc()


class QueuedOr(QueuedOp):
    a: QueuedOp
    b: QueuedOp

    def __init__(
        self, qc: QuantumCircuit, anc: List[AncillaQubit], a: QueuedOp, b: QueuedOp
    ):
        self.qc = qc
        self.anc = anc
        self.a = a
        self.b = b

    def execute(self, target: QuantumRegister):
        # print(f"{target} = {self.a} | {self.b}")

        a1 = self.a.prepare_anc()
        a2 = self.b.prepare_anc()

        self.qc.reset(target)

        self.qc.cx(a1, target)
        self.qc.cx(a2, target)
        self.qc.ccx(a1, a2, target)

        self.a.drop_anc()
        self.b.drop_anc()


class QueuedAnd(QueuedOp):
    a: QueuedOp
    b: QueuedOp

    def __init__(
        self, qc: QuantumCircuit, anc: List[AncillaQubit], a: QueuedOp, b: QueuedOp
    ):
        self.qc = qc
        self.anc = anc
        self.a = a
        self.b = b

    def execute(self, target: QuantumRegister):
        # print(f"{target} = {self.a} & {self.b}")

        a1 = self.a.prepare_anc()
        a2 = self.b.prepare_anc()

        self.qc.reset(target)
        self.qc.ccx(a1, a2, target)

        self.a.drop_anc()
        self.b.drop_anc()


class QueuedNotEqual(QueuedOp):
    a: QueuedOp
    b: QueuedOp

    def __init__(
        self, qc: QuantumCircuit, anc: List[AncillaQubit], a: QueuedOp, b: QueuedOp
    ):
        self.qc = qc
        self.anc = anc
        self.a = a
        self.b = b

    def execute(self, target: QuantumRegister):
        # print(f"{target} = {self.a} != {self.b}")

        a1 = self.a.prepare_anc()

        self.b.execute(target)
        self.qc.cx(a1, target)

        self.a.drop_anc()


class QueuedEqual(QueuedOp):
    a: QueuedOp
    b: QueuedOp

    def __init__(
        self, qc: QuantumCircuit, anc: List[AncillaQubit], a: QueuedOp, b: QueuedOp
    ):
        self.anc = anc
        self.qc = qc
        self.a = a
        self.b = b

    def execute(self, target: QuantumRegister):
        # print(f"{target} = {self.a} == {self.b}")

        a1 = self.a.prepare_anc()

        # a2 = True
        a2 = self.anc.pop()
        self.qc.reset(a2)
        self.qc.x(a2)

        self.b.execute(target)

        self.qc.cx(a1, target)
        self.qc.cx(a2, target)

        self.a.drop_anc()
        self.anc.append(a2)

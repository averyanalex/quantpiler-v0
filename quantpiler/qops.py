from typing import List

from qiskit.circuit.quantumregister import Qubit, AncillaQubit
from qiskit.circuit import QuantumCircuit


class QueuedOp:
    qc: QuantumCircuit
    anc: List[AncillaQubit]

    def isQubit(self) -> bool:
        return False


class QueuedQubit(QueuedOp):
    value: Qubit

    def __init__(self, qc: QuantumCircuit, anc: List[AncillaQubit], value: Qubit):
        self.qc = qc
        self.anc = anc
        self.value = value

    def isQubit(self) -> bool:
        return True

    def execute(self, target: Qubit):
        print(f"{target} = {self.value}")
        self.qc.reset(target)
        self.qc.cx(self.value, target)


class QueuedBool(QueuedOp):
    value: bool

    def __init__(self, qc: QuantumCircuit, anc: List[AncillaQubit], value: bool):
        self.qc = qc
        self.anc = anc
        self.value = value

    def execute(self, target: Qubit):
        print(f"{target} = {self.value}")
        self.qc.reset(target)
        if self.value:
            self.qc.x(target)


class QueuedNot(QueuedOp):
    a: QueuedOp

    def __init__(self, qc: QuantumCircuit, anc: List[AncillaQubit], a: QueuedOp):
        self.qc = qc
        self.anc = anc
        self.a = a

    def execute(self, target: Qubit):
        print(f"{target} = not {self.a}")

        if self.a.isQubit():
            a1 = self.a.value
        else:
            a1 = self.anc.pop()
            self.a.execute(a1)

        self.qc.reset(target)
        self.qc.x(target)

        self.qc.cx(a1, target)

        if not self.a.isQubit():
            self.anc.append(a1)


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

    def execute(self, target: Qubit):
        print(f"{target} = {self.a} | {self.b}")

        if self.a.isQubit():
            a1 = self.a.value
        else:
            a1 = self.anc.pop()
            self.a.execute(a1)

        if self.b.isQubit():
            a2 = self.b.value
        else:
            a2 = self.anc.pop()
            self.b.execute(a2)

        self.qc.reset(target)

        self.qc.cx(a1, target)
        self.qc.cx(a2, target)
        self.qc.ccx(a1, a2, target)

        if not self.a.isQubit():
            self.anc.append(a1)
        if not self.b.isQubit():
            self.anc.append(a2)


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

    def execute(self, target: Qubit):
        print(f"{target} = {self.a} & {self.b}")

        if self.a.isQubit():
            a1 = self.a.value
        else:
            a1 = self.anc.pop()
            self.a.execute(a1)

        if self.b.isQubit():
            a2 = self.b.value
        else:
            a2 = self.anc.pop()
            self.b.execute(a2)

        self.qc.reset(target)

        self.qc.ccx(a1, a2, target)

        if not self.a.isQubit():
            self.anc.append(a1)
        if not self.b.isQubit():
            self.anc.append(a2)


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

    def execute(self, target: Qubit):
        print(f"{target} = {self.a} != {self.b}")

        if self.a.isQubit():
            a1 = self.a.value
        else:
            a1 = self.anc.pop()
            self.a.execute(a1)

        self.b.execute(target)

        self.qc.cx(a1, target)

        if not self.a.isQubit():
            self.anc.append(a1)


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

    def execute(self, target: Qubit):
        print(f"{target} = {self.a} == {self.b}")

        if self.a.isQubit():
            a1 = self.a.value
        else:
            a1 = self.anc.pop()
            self.a.execute(a1)

        a2 = self.anc.pop()
        self.qc.reset(a2)
        self.qc.x(a2)

        self.b.execute(target)

        self.qc.cx(a1, target)
        self.qc.cx(a2, target)

        if not self.a.isQubit():
            self.anc.append(a1)
        self.anc.append(a2)

import dis

from qiskit.circuit.quantumregister import Qubit, AncillaQubit
from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit


def compile(func, ancillas_count: int):
    input_qubits = {}
    tmp_qubits = {}
    all_qubits = {}

    input_args_count = func.__code__.co_argcount
    varnames = func.__code__.co_varnames

    for i in range(len(varnames)):
        name = varnames[i]
        if i < input_args_count:
            input_qubits[name] = Qubit()
        else:
            tmp_qubits[name] = Qubit()

    all_qubits = input_qubits | tmp_qubits

    input_qr = QuantumRegister(bits=list(input_qubits.values()))
    tmp_qr = QuantumRegister(bits=list(tmp_qubits.values()))

    ancillas: [Qubit] = []
    for i in range(ancillas_count):
        ancillas.append(AncillaQubit())

    ancilla_qr = AncillaRegister(bits=ancillas)

    qc = QuantumCircuit(input_qr, tmp_qr, ancilla_qr, name='test')

    class QueuedOp:
        def __init__(self):
            pass

        def isQubit(self) -> bool:
            return False

        def execute(self, target: Qubit):
            print("Oh no execute not working!!!")

    class QueuedQubit(QueuedOp):
        value: Qubit

        def __init__(self, value: Qubit):
            self.value = value

        def isQubit(self) -> bool:
            return True

        def execute(self, target: Qubit):
            print(f"{target} = {self.value}")
            qc.reset(target)
            qc.cx(self.value, target)

    class QueuedBool(QueuedOp):
        value: bool

        def __init__(self, value: bool):
            self.value = value

        def execute(self, target: Qubit):
            print(f"{target} = {self.value}")
            qc.reset(target)
            if self.value:
                qc.x(target)

    class QueuedNot(QueuedOp):
        a: QueuedOp

        def __init__(self, a: QueuedOp):
            self.a = a

        def execute(self, target: Qubit):
            print(f"{target} = not {self.a}")

            if a.isQubit():
                a1 = self.a.value
            else:
                a1 = ancillas.pop()
                self.a.execute(a1)

            qc.reset(target)
            qc.x(target)

            qc.cx(a1, target)

            if not a.isQubit():
                ancillas.append(a1)

    class QueuedOr(QueuedOp):
        a: QueuedOp
        b: QueuedOp

        def __init__(self, a: QueuedOp, b: QueuedOp):
            self.a = a
            self.b = b

        def execute(self, target: Qubit):
            print(f"{target} = {self.a} | {self.b}")

            if a.isQubit():
                a1 = self.a.value
            else:
                a1 = ancillas.pop()
                self.a.execute(a1)

            if b.isQubit():
                a2 = self.b.value
            else:
                a2 = ancillas.pop()
                self.b.execute(a2)

            qc.reset(target)

            qc.cx(a1, target)
            qc.cx(a2, target)
            qc.ccx(a1, a2, target)

            if not a.isQubit():
                ancillas.append(a1)
            if not b.isQubit():
                ancillas.append(a2)

    class QueuedAnd(QueuedOp):
        a: QueuedOp
        b: QueuedOp

        def __init__(self, a: QueuedOp, b: QueuedOp):
            self.a = a
            self.b = b

        def execute(self, target: Qubit):
            print(f"{target} = {self.a} & {self.b}")

            if a.isQubit():
                a1 = self.a.value
            else:
                a1 = ancillas.pop()
                self.a.execute(a1)

            if b.isQubit():
                a2 = self.b.value
            else:
                a2 = ancillas.pop()
                self.b.execute(a2)

            qc.reset(target)

            qc.ccx(a1, a2, target)

            if not a.isQubit():
                ancillas.append(a1)
            if not b.isQubit():
                ancillas.append(a2)

    class QueuedNotEqual(QueuedOp):
        a: QueuedOp
        b: QueuedOp

        def __init__(self, a: QueuedOp, b: QueuedOp):
            self.a = a
            self.b = b

        def execute(self, target: Qubit):
            print(f"{target} = {self.a} != {self.b}")

            if a.isQubit():
                a1 = self.a.value
            else:
                a1 = ancillas.pop()
                self.a.execute(a1)

            self.b.execute(target)

            qc.cx(a1, target)

            if not a.isQubit():
                ancillas.append(a1)

    class QueuedEqual(QueuedOp):
        a: QueuedOp
        b: QueuedOp

        def __init__(self, a: QueuedOp, b: QueuedOp):
            self.a = a
            self.b = b

        def execute(self, target: Qubit):
            print(f"{target} = {self.a} == {self.b}")

            if a.isQubit():
                a1 = self.a.value
            else:
                a1 = ancillas.pop()
                self.a.execute(a1)

            a2 = ancillas.pop()
            qc.reset(a2)
            qc.x(a2)

            self.b.execute(target)

            qc.cx(a1, target)
            qc.cx(a2, target)

            if not a.isQubit():
                ancillas.append(a1)
            ancillas.append(a2)

    stack: [QueuedOp] = []

    bc = dis.Bytecode(func)
    for inst in bc:
        opname = inst.opname

        if opname == 'LOAD_FAST':
            target = all_qubits[inst.argval]
            stack.append(QueuedQubit(target))

        elif opname == 'LOAD_CONST':
            const = inst.argval
            stack.append(QueuedBool(const))

        elif opname == 'STORE_FAST':
            op = stack.pop()
            target = all_qubits[inst.argval]
            op.execute(target)

        elif opname == 'BINARY_OR':
            a = stack.pop()
            b = stack.pop()
            stack.append(QueuedOr(a, b))

        elif opname == 'UNARY_NOT':
            a = stack.pop()
            stack.append(QueuedNot(a))

        elif opname == 'BINARY_AND':
            a = stack.pop()
            b = stack.pop()
            stack.append(QueuedAnd(a, b))

        elif opname == 'COMPARE_OP':
            optype = inst.argval
            if optype == '!=':
                a = stack.pop()
                b = stack.pop()
                stack.append(QueuedNotEqual(a, b))
            elif optype == '==':
                a = stack.pop()
                b = stack.pop()
                stack.append(QueuedEqual(a, b))
            else:
                print(f"{inst.argval} unsupported")

        elif opname == 'RETURN_VALUE':
            pass

        else:
            print(f"Operation {inst} unsupported")

    return qc

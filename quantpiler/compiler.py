"""
Python -> QuantumCircuit compiler.
"""

from typing import Callable, Dict, List

import ast
import inspect
import textwrap

from qiskit.circuit.quantumregister import Qubit, AncillaQubit
from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit


def get_args_vars(func: Callable) -> Dict[str, int]:
    args_vars: Dict[str, int] = {}

    st = get_ast(func)
    args = st.body[0].args.args
    for arg in args:
        args_vars[arg.arg] = arg.annotation.value

    return args_vars


def get_return_size(func: Callable) -> int:
    st = get_ast(func)
    try:
        return st.body[0].returns.value
    except AttributeError:
        return 0


def get_ast(module) -> ast.AST:
    source = inspect.getsource(module)
    source = textwrap.dedent(source)
    st = ast.parse(source)
    return st


def get_min_reg(*regs: QuantumRegister) -> int:
    flat_regs: List[QuantumRegister] = []
    for r in regs:
        if type(r) == QuantumRegister:
            flat_regs.append(r)
        else:
            flat_regs.extend(r)

    sizes: List[int] = []
    for reg in flat_regs:
        sizes.append(len(reg))

    return min(sizes)


def get_used_vars(op: ast.AST) -> List[str]:
    variables: List[str] = []

    def guv(_op: ast.AST, _vars: List[str]):
        op_type = type(_op)

        if op_type == ast.Name:
            _vars.append(_op.id)
        elif op_type == ast.UnaryOp:
            guv(_op.operand, _vars)
        elif op_type == ast.BinOp:
            for val in [_op.left, _op.right]:
                guv(val, _vars)
        else:
            raise NotImplementedError()

    guv(op, variables)
    return variables


def unwrap_ops_chain(op: ast.AST, t: ast.AST) -> List[ast.AST]:
    sources: List[ast.AST] = []

    def unwrap_op(_op: ast.AST, _sources: List[ast.AST]):
        for side in [_op.left, _op.right]:
            if type(side) == ast.BinOp and type(side.op) == t:
                unwrap_op(side, _sources)
            else:
                _sources.append(side)

    unwrap_op(op, sources)
    return sources


class Compiler:
    qc: QuantumCircuit
    variables: Dict[str, QuantumRegister]
    ret: QuantumRegister
    ancillas: List[AncillaQubit]

    def __init__(self):
        self.variables = {}
        self.ancillas = []

    def set_qc(self, qc: QuantumCircuit):
        self.qc = qc

    def assemble(self, func: Callable) -> QuantumCircuit:
        args_vars = get_args_vars(func)
        for arg_name, arg_bitness in args_vars.items():
            self.variables[arg_name] = QuantumRegister(arg_bitness, name=arg_name)

        ret_size = get_return_size(func)
        self.ret = QuantumRegister(ret_size, name="return")

        self.qc = QuantumCircuit(*self.variables.values(), self.ret, name=func.__name__)

        st = get_ast(func)
        self.assemble_function(st.body[0])

    def get_qc(self) -> QuantumCircuit:
        return self.qc

    def get_ret(self) -> QuantumRegister:
        return self.ret

    def assemble_function(self, func: ast.AST):
        for inst in func.body:
            print(ast.dump(inst, indent=4))
            # self.qc.barrier()
            self.assemble_instruction(inst)

    def assemble_instruction(self, instruction: ast.AST):
        inst_type = type(instruction)

        if inst_type == ast.Assign:
            target = self.variables[instruction.targets[0].id]
        elif inst_type == ast.AnnAssign:
            target = self.variables[instruction.target.id]
        elif inst_type == ast.Return:
            target = self.ret
        else:
            raise NotImplementedError(f"Unsupported top-level operation: {inst_type}")

        self.assemble_op(instruction.value, target)

    def assemble_op(self, op: ast.AST, target: QuantumRegister):
        op_type = type(op)
        if op_type == ast.UnaryOp:
            source = self.value_to_reg(op.operand)

            op_subtype = type(op.op)
            if op_subtype == ast.Invert:
                self.assemble_invert(source, target)
            else:
                raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")

            self.drop_ancilla_reg(source)

        elif op_type == ast.BinOp:
            op_subtype = type(op.op)
            if op_subtype == ast.BitXor:
                sources = self.values_to_regs(unwrap_ops_chain(op, ast.BitXor))
                self.assemble_xor(sources, target)
                self.drop_ancilla_regs(sources)
            elif op_subtype == ast.BitAnd:
                sources = self.values_to_regs(unwrap_ops_chain(op, ast.BitAnd))
                self.assemble_bit_and(sources, target)
                self.drop_ancilla_regs(sources)
            elif op_subtype == ast.BitOr:
                sources = self.values_to_regs(unwrap_ops_chain(op, ast.BitOr))
                self.assemble_bit_or(sources, target)
                self.drop_ancilla_regs(sources)
            else:
                raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")
        else:
            raise NotImplementedError(f"Unsupported operation: {op_type}")

    def get_max_used_var(self, op: ast.AST) -> int:
        anc_size = 0
        for var in get_used_vars(op):
            if len(self.variables[var]) > anc_size:
                anc_size = len(self.variables[var])
        return anc_size

    def value_to_reg(self, value: ast.AST) -> QuantumRegister:
        if type(value) == ast.Name:
            return self.variables[value.id]
        else:
            max_size = self.get_max_used_var(value)
            reg = self.get_ancilla_reg(max_size)
            self.assemble_op(value, reg)
            return reg

    def values_to_regs(self, values: List[ast.AST]) -> List[QuantumRegister]:
        regs: List[QuantumRegister] = []

        for val in values:
            regs.append(self.value_to_reg(val))

        return regs

    def get_ancilla(self) -> AncillaQubit:
        if len(self.ancillas) == 0:
            new_anc = AncillaQubit()
            new_anc_reg = AncillaRegister(bits=[new_anc])
            self.qc.add_register(new_anc_reg)
            return new_anc
        else:
            return self.ancillas.pop()

    def get_ancilla_reg(self, size: int) -> AncillaRegister:
        bits: List[AncillaQubit] = []
        for i in range(size):
            bits.append(self.get_ancilla())

        return AncillaRegister(bits=bits)

    def drop_ancilla(self, anc: AncillaQubit):
        self.ancillas.append(anc)

    def drop_ancilla_reg(self, reg: AncillaRegister):
        if type(reg) == AncillaRegister:
            for bit in reg:
                self.drop_ancilla(bit)

    def drop_ancilla_regs(self, regs: List[AncillaRegister]):
        for reg in regs:
            self.drop_ancilla_reg(reg)

    def assemble_invert(self, source: QuantumRegister, target: QuantumRegister):
        if source == target:
            self.qc.x(source)
        else:
            self.qc.reset(target)
            self.qc.x(target)
            for i in range(min(len(source), len(target))):
                self.qc.cx(source[i], target[i])

    def assemble_xor(self, sources: List[QuantumRegister], target: QuantumRegister):
        if target in sources:
            sources.remove(target)
        else:
            self.qc.reset(target)

        for src in sources:
            for i in range(min(len(src), len(target))):
                self.qc.cx(src[i], target[i])

    def assemble_bit_and(self, sources: List[QuantumRegister], target: QuantumRegister):
        if target in sources:
            sources.remove(target)

            for i in range(len(target)):
                src_qubits: List[Qubit] = []

                for src_reg in sources:
                    if len(src_reg) >= i + 1:
                        src_qubits.append(src_reg[i])

                if len(src_qubits) > 0:
                    src_qubits.append(target[i])

                    anc = self.get_ancilla()
                    self.qc.reset(anc)

                    self.qc.mcx(src_qubits, anc)
                    self.qc.swap(anc, target[i])

                    self.drop_ancilla(anc)
                else:
                    self.qc.reset(target[i])
        else:
            self.qc.reset(target)
            for i in range(get_min_reg(sources, target)):
                src_qubits: List[Qubit] = []
                for src_reg in sources:
                    src_qubits.append(src_reg[i])

                self.qc.mcx(src_qubits, target[i])

    def assemble_bit_or(self, sources: List[QuantumRegister], target: QuantumRegister):
        if target in sources:
            raise NotImplementedError()
        else:
            self.qc.reset(target)
            for i in range(len(target)):
                src_qubits: List[Qubit] = []
                for src_reg in sources:
                    if len(src_reg) >= i + 1:
                        src_qubits.append(src_reg[i])

                if len(src_qubits) > 0:
                    self.qc.x(src_qubits)
                    self.qc.x(target[i])
                    self.qc.mcx(src_qubits, target[i])
                    self.qc.x(src_qubits)


# def assemble(func: Callable) -> QuantumCircuit:
#     """Compile python function to qiskit circuit.

#     Args:
#         func (Callable): Function to compile.

#     Raises:
#         NotImplementedError: Some of used operations aren't supported yet.

#     Returns:
#         QuantumCircuit: Compiled circuit.
#     """

#     variables: Dict[str, QuantumRegister] = {}
#     ancillas: List[AncillaQubit] = []

#     args_vars = get_args_vars(func)
#     for arg_name, arg_bitness in args_vars.items():
#         variables[arg_name] = QuantumRegister(arg_bitness, name=arg_name)

#     qc = QuantumCircuit(*variables.values(), name=func.__name__)

#     return qc

"""
Python -> QuantumCircuit compiler.
"""

from typing import Callable, Dict, List

import ast
import inspect

from qiskit.circuit.quantumregister import Qubit, AncillaQubit
from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit


def get_args_vars(func: Callable):
    args_vars: Dict[str, int] = {}

    st = get_ast(func)
    args = st.body[0].args.args
    for arg in args:
        args_vars[arg.arg] = arg.annotation.value

    return args_vars


def get_ast(module) -> ast.AST:
    source = inspect.getsource(module)
    st = ast.parse(source)
    return st


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


def get_used_vars(op: ast.AST) -> List[str]:
    variables: List[str] = []

    def guv(_op: ast.AST, _vars: List[str]):
        op_type = type(_op)

        if op_type == ast.Name:
            _vars.append(_op.id)
        elif op_type == ast.UnaryOp:
            guv(_op.value, _vars)
        elif op_type == ast.BinOp:
            for val in [_op.left, _op.right]:
                guv(val, _vars)
        else:
            raise NotImplementedError()

    guv(op, variables)
    return variables


def get_max_used_var(op: ast.AST, variables: Dict[str, QuantumRegister]) -> int:
    anc_size = 0
    for var in get_used_vars(op):
        if len(variables[var]) > anc_size:
            anc_size = len(variables[var])
    return anc_size


def assemble_invert(
    qc: QuantumCircuit, source: QuantumRegister, target: QuantumRegister
):
    if source == target:
        qc.x(source)
    else:
        qc.reset(target)
        qc.x(target)
        for i in range(min(len(source), len(target))):
            qc.cx(source[i], target[i])


def assemble_xor(
    qc: QuantumCircuit, sources: List[QuantumRegister], target: QuantumRegister
):
    if target in sources:
        sources.remove(target)
    else:
        qc.reset(target)

    for src in sources:
        for i in range(min(len(src), len(target))):
            qc.cx(src[i], target[i])


def assemble_bit_and(
    qc: QuantumCircuit,
    sources: List[QuantumRegister],
    ancillas: List[AncillaQubit],
    target: QuantumRegister,
):
    if target in sources:
        sources.remove(target)

        for i in range(len(target)):
            src_qubits: List[Qubit] = []

            for src_reg in sources:
                if len(src_reg) >= i + 1:
                    src_qubits.append(src_reg[i])

            if len(src_qubits) > 0:
                src_qubits.append(target[i])

                anc = get_ancilla(qc, ancillas)
                qc.reset(anc)

                qc.mcx(src_qubits, anc)
                qc.swap(anc, target[i])

                drop_ancilla(qc, ancillas, anc)
            else:
                qc.reset(target[i])
    else:
        qc.reset(target)
        for i in range(len(target)):
            src_qubits: List[Qubit] = []
            for src_reg in sources:
                if len(src_reg) >= i + 1:
                    src_qubits.append(src_reg[i])

            if len(src_qubits) > 0:
                qc.mcx(src_qubits, target[i])


def assemble_bit_or(
    qc: QuantumCircuit,
    sources: List[QuantumRegister],
    ancillas: List[AncillaQubit],
    target: QuantumRegister,
):
    if target in sources:
        raise NotImplementedError()
    else:
        qc.reset(target)
        for i in range(len(target)):
            src_qubits: List[Qubit] = []
            for src_reg in sources:
                if len(src_reg) >= i + 1:
                    src_qubits.append(src_reg[i])

            if len(src_qubits) > 0:
                qc.x(src_qubits)
                qc.x(target[i])
                qc.mcx(src_qubits, target[i])
                qc.x(src_qubits)


def get_ancilla(qc: QuantumCircuit, ancillas: List[AncillaQubit]) -> AncillaQubit:
    if len(ancillas) == 0:
        new_anc = AncillaQubit()
        new_anc_reg = AncillaRegister(bits=[new_anc])
        qc.add_register(new_anc_reg)
        return new_anc
    else:
        return ancillas.pop()


def drop_ancilla(qc: QuantumCircuit, ancillas: List[AncillaQubit], anc: AncillaQubit):
    ancillas.append(anc)


def get_ancilla_reg(
    qc: QuantumCircuit, ancillas: List[AncillaQubit], size: int
) -> AncillaRegister:
    bits: List[AncillaQubit] = []
    for i in range(size):
        bits.append(get_ancilla(qc, ancillas))

    return AncillaRegister(bits=bits)


def drop_ancilla_reg(
    qc: QuantumCircuit, ancillas: List[AncillaQubit], reg: AncillaRegister
):
    if type(reg) == AncillaRegister:
        for bit in reg:
            drop_ancilla(qc, ancillas, bit)


def drop_ancilla_regs(
    qc: QuantumCircuit, ancillas: List[AncillaQubit], regs: List[AncillaRegister]
):
    for reg in regs:
        drop_ancilla_reg(qc, ancillas, reg)


def value_to_reg(
    qc: QuantumCircuit,
    value: ast.AST,
    variables: Dict[str, QuantumRegister],
    ancillas: List[AncillaQubit],
) -> QuantumRegister:
    if type(value) == ast.Name:
        return variables[value.id]
    else:
        max_size = get_max_used_var(value, variables)
        reg = get_ancilla_reg(qc, ancillas, max_size)
        assemble_op(qc, variables, ancillas, reg, value)
        return reg


def values_to_regs(
    qc: QuantumCircuit,
    values: List[ast.AST],
    variables: Dict[str, QuantumRegister],
    ancillas: List[AncillaQubit],
) -> List[QuantumRegister]:
    regs: List[QuantumRegister] = []

    for val in values:
        regs.append(value_to_reg(qc, val, variables, ancillas))

    return regs


def assemble_op(
    qc: QuantumCircuit,
    variables: Dict[str, QuantumRegister],
    ancillas: List[AncillaQubit],
    target: QuantumRegister,
    op: ast.AST,
):
    op_type = type(op)
    if op_type == ast.UnaryOp:
        source = value_to_reg(qc, op.operand, variables, ancillas)

        op_subtype = type(op.op)
        if op_subtype == ast.Invert:
            assemble_invert(qc, source, target)
        else:
            raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")

        drop_ancilla_reg(qc, ancillas, source)

    elif op_type == ast.BinOp:
        op_subtype = type(op.op)
        if op_subtype == ast.BitXor:
            sources = values_to_regs(
                qc, unwrap_ops_chain(op, ast.BitXor), variables, ancillas
            )
            assemble_xor(qc, sources, target)
            drop_ancilla_regs(qc, ancillas, sources)
        elif op_subtype == ast.BitAnd:
            sources = values_to_regs(
                qc, unwrap_ops_chain(op, ast.BitAnd), variables, ancillas
            )
            assemble_bit_and(qc, sources, ancillas, target)
            drop_ancilla_regs(qc, ancillas, sources)
        elif op_subtype == ast.BitOr:
            sources = values_to_regs(
                qc, unwrap_ops_chain(op, ast.BitOr), variables, ancillas
            )
            assemble_bit_or(qc, sources, ancillas, target)
            drop_ancilla_regs(qc, ancillas, sources)
        else:
            raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")
    else:
        raise NotImplementedError(f"Unsupported operation: {op_type}")


def assemble_instruction(
    qc: QuantumCircuit,
    variables: Dict[str, QuantumRegister],
    ancillas: List[AncillaQubit],
    instruction: ast.AST,
):
    inst_type = type(instruction)

    if inst_type == ast.Assign:
        target = variables[instruction.targets[0].id]
    elif inst_type == ast.AnnAssign:
        target = variables[instruction.target.id]
    else:
        raise NotImplementedError(f"Unsupported top-level operation: {inst_type}")

    assemble_op(qc, variables, ancillas, target, instruction.value)


def assemble_function(
    qc: QuantumCircuit,
    func: Callable,
    variables: Dict[str, QuantumRegister],
    ancillas: List[AncillaQubit],
):
    st = get_ast(func)
    instructions = st.body[0].body

    for inst in instructions:
        print(ast.dump(inst, indent=4))
        qc.barrier()
        assemble_instruction(qc, variables, ancillas, inst)


def assemble(func: Callable) -> QuantumCircuit:
    """Compile python function to qiskit circuit.

    Args:
        func (Callable): Function to compile.

    Raises:
        NotImplementedError: Some of used operations aren't supported yet.

    Returns:
        QuantumCircuit: Compiled circuit.
    """

    variables: Dict[str, QuantumRegister] = {}
    ancillas: List[AncillaQubit] = []

    args_vars = get_args_vars(func)
    for arg_name, arg_bitness in args_vars.items():
        variables[arg_name] = QuantumRegister(arg_bitness, name=arg_name)

    qc = QuantumCircuit(*variables.values(), name=func.__name__)

    assemble_function(qc, func, variables, ancillas)

    return qc

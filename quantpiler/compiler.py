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


def unwrap_xor_chain(op: ast.BinOp) -> List[ast.AST]:
    sources: List[ast.AST] = []

    def unwrap_xor(_op: ast.BinOp, _sources: List[ast.AST]):
        if type(_op.left) == ast.BinOp:
            if type(_op.left.op) == ast.BitXor:
                unwrap_xor(_op.left, _sources)
            else:
                _sources.append(_op.left)
        else:
            _sources.append(_op.left)

        if type(_op.right) == ast.BinOp:
            if type(_op.right.op) == ast.BitXor:
                unwrap_xor(_op.right, _sources)
            else:
                _sources.append(_op.right)
        else:
            _sources.append(_op.right)

    unwrap_xor(op, sources)
    return sources


def values_to_regs(
    qc: QuantumCircuit, values: List[ast.AST], variables: Dict[str, QuantumRegister]
) -> List[QuantumRegister]:
    regs: List[QuantumRegister] = []

    for val in values:
        if type(val) == ast.Name:
            regs.append(variables[val.id])
        else:
            # anc = get_ancilla_reg()
            # assemble_op(qc, variables, anc, val)
            # regs.append(anc)
            raise NotImplementedError(f"Ancillas not implemented")

    return regs


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


def value_to_reg(
    qc: QuantumCircuit, value: ast.AST, variables: Dict[str, QuantumRegister]
) -> QuantumRegister:
    if type(value) == ast.Name:
        return variables[value.id]
    else:
        raise NotImplementedError(f"Ancillas not implemented")


def assemble_op(
    qc: QuantumCircuit,
    variables: Dict[str, QuantumRegister],
    target: QuantumRegister,
    op: ast.AST,
):
    op_type = type(op)
    if op_type == ast.UnaryOp:
        source = value_to_reg(qc, op.operand, variables)

        op_subtype = type(op.op)
        if op_subtype == ast.Invert:
            assemble_invert(qc, source, target)
        else:
            raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")

    elif op_type == ast.BinOp:
        op_subtype = type(op.op)
        if op_subtype == ast.BitXor:
            sources = values_to_regs(qc, unwrap_xor_chain(op), variables)
            assemble_xor(qc, sources, target)
        else:
            raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")
    else:
        raise NotImplementedError(f"Unsupported operation: {op_type}")


def assemble_instruction(
    qc: QuantumCircuit, variables: Dict[str, QuantumRegister], instruction: ast.AST
):
    inst_type = type(instruction)

    if inst_type == ast.Assign:
        target = variables[instruction.targets[0].id]
        assemble_op(qc, variables, target, instruction.value)
    elif inst_type == ast.AnnAssign:
        target = variables[instruction.target.id]
        assemble_op(qc, variables, target, instruction.value)
    else:
        raise NotImplementedError(f"Unsupported top-level operation: {inst_type}")


def assemble_function(
    qc: QuantumCircuit, func: Callable, variables: Dict[str, QuantumRegister]
):
    st = get_ast(func)
    instructions = st.body[0].body

    for inst in instructions:
        print(ast.dump(inst, indent=4))
        qc.barrier()
        assemble_instruction(qc, variables, inst)


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

    args_vars = get_args_vars(func)
    for arg_name, arg_bitness in args_vars.items():
        variables[arg_name] = QuantumRegister(arg_bitness, name=arg_name)

    qc = QuantumCircuit(*variables.values(), name=func.__name__)

    assemble_function(qc, func, variables)

    return qc

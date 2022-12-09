"""
Python -> QuantumCircuit compiler.
"""

from typing import Callable, Dict, List, Union

import ast
import inspect
import textwrap

from qiskit.circuit.quantumregister import Qubit, AncillaQubit
from qiskit import QuantumRegister, AncillaRegister
from qiskit.circuit import QuantumCircuit

from .qreg import QReg


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
    qc: QuantumCircuit = None
    variables: Dict[str, QReg] = {}
    conditions: List[Qubit] = []
    check_cond: bool = False
    ret: QReg = None
    bits: List[Qubit] = []

    def __init__(self):
        self.qc = None
        self.variables = {}
        self.conditions = []
        self.check_cond = False
        self.ret = None
        self.bits = []

    def set_qc(self, qc: QuantumCircuit):
        self.qc = qc

    def assemble(self, func: Callable) -> QuantumCircuit:
        # Create quantum circuit
        self.qc = QuantumCircuit(name=func.__name__)

        # Create qreg for every function's argument
        args_vars = get_args_vars(func)
        for arg_name, arg_bitness in args_vars.items():
            self.variables[arg_name] = self.create_reg(arg_bitness)

        # Compile function
        st = get_ast(func)
        self.assemble_function(st.body[0])

    def get_qc(self) -> QuantumCircuit:
        return self.qc

    def get_ret(self) -> QuantumRegister:
        return self.ret

    def assemble_function(self, func: ast.AST):
        self.assemble_instructions(func.body)

    def assemble_instructions(self, instructions: List[ast.AST]):
        for inst in instructions:
            self.assemble_instruction(inst)

    def assemble_instruction(self, instruction: ast.AST):
        inst_type = type(instruction)

        if inst_type == ast.Assign:
            if len(instruction.targets) != 1:
                raise NotImplementedError(f"Assign to multiple variables")
            var_name = instruction.targets[0].id

            self.variables[var_name] = self.assemble_op(
                instruction.value, check_cond=True
            )
        # elif inst_type == ast.AnnAssign:
        #     var_name = instruction.target.id
        elif inst_type == ast.Return:
            if type(instruction.value) == ast.Name:
                self.ret = self.variables[instruction.value.id]
            else:
                self.ret = self.assemble_op(instruction.value)
        elif inst_type == ast.If:
            # Calculate bool bit from if's test
            test_res = self.assemble_op(instruction.test)

            if len(self.conditions) == 0:
                # If is is first if just add cond to conditions
                cur_cond = self.assemble_to_bool(test_res)
                self.conditions.append(cur_cond)
            else:
                # If there is already conditions calculate (past and current)
                past_cond = self.conditions.pop()
                res_cond = self.assemble_to_bool(test_res, prev=past_cond)
                self.conditions.append(past_cond)
                self.conditions.append(res_cond)

            if type(instruction.test) != ast.Name:
                self.destroy_reg(test_res)

            self.assemble_instructions(instruction.body)

            last_cond = self.conditions.pop()
            self.drop_bit(last_cond)
        else:
            raise NotImplementedError(f"Unsupported top-level operation: {inst_type}")

    def assemble_op(self, op: ast.AST, check_cond: bool = False) -> QReg:
        def wrap_op_cond_check(call: Callable, args) -> QReg:
            if check_cond:
                self.check_cond = True

            res = call(args)

            if check_cond:
                self.check_cond = False

            return res

        op_type = type(op)
        if op_type == ast.Name:
            # TODO: check cond
            res = self.variables[op.id]

        elif op_type == ast.UnaryOp:
            source = self.value_to_reg(op.operand)

            op_subtype = type(op.op)
            if op_subtype == ast.Invert:
                res = wrap_op_cond_check(self.assemble_invert, source)
            else:
                raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")

            self.drop_tmp_reg(source)

        elif op_type == ast.BinOp:
            op_subtype = type(op.op)
            if op_subtype == ast.BitXor:
                sources = self.values_to_regs(unwrap_ops_chain(op, ast.BitXor))
                res = wrap_op_cond_check(self.assemble_xor, sources)
                self.drop_tmp_regs(sources)
            elif op_subtype == ast.BitAnd:
                sources = self.values_to_regs(unwrap_ops_chain(op, ast.BitAnd))
                res = wrap_op_cond_check(self.assemble_bit_and, sources)
                self.drop_tmp_regs(sources)
            elif op_subtype == ast.BitOr:
                sources = self.values_to_regs(unwrap_ops_chain(op, ast.BitOr))
                res = wrap_op_cond_check(self.assemble_bit_or, sources)
                self.drop_tmp_regs(sources)
            else:
                raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")
        else:
            raise NotImplementedError(f"Unsupported operation: {op_type}")

        self.qc.barrier()

        return res

    def value_to_reg(self, value: ast.AST) -> QReg:
        if type(value) == ast.Name:
            return self.variables[value.id]
        else:
            reg = self.assemble_op(value)
            reg.tmp = True
            return reg

    def values_to_regs(self, values: List[ast.AST]) -> List[QReg]:
        regs: List[QReg] = []

        for val in values:
            regs.append(self.value_to_reg(val))

        return regs

    def add_bit_to_qc(self, bit: Qubit):
        reg = QuantumRegister(bits=[bit])
        self.qc.add_register(reg)
        # self.qc.add_bits([bit])

    def get_bit(self) -> Qubit:
        if len(self.bits) == 0:
            bit = Qubit()
            self.add_bit_to_qc(bit)
            return bit
        else:
            bit = self.bits.pop()
            self.qc.reset(bit)
            return bit

    def drop_bit(self, bit: Qubit):
        self.bits.append(bit)

    def create_reg(self, size: int) -> QReg:
        bits: List[Qubit] = []
        for _ in range(size):
            bits.append(self.get_bit())

        reg = QReg(bits=bits)
        # reg.qc = self.qc
        return reg

    def destroy_reg(self, reg: QReg):
        for bit in reg:
            self.drop_bit(bit)

    def resize_reg(self, reg: QReg, size: int) -> QReg:
        if size <= 0:
            raise NotImplementedError("You are ananas")

        bits: List[Qubit] = []
        for bit in reg:
            bits.append(bit)

        if size > len(reg):
            for _ in range(size - len(reg)):
                bits.append(self.get_bit())
        elif size < len(reg):
            for _ in range(len(reg) - size):
                self.drop_bit(bits.pop())

        new_reg = QReg(bits=bits)
        new_reg.tmp = reg.tmp
        return new_reg

    def drop_tmp_reg(self, reg: QReg):
        if reg.tmp:
            self.destroy_reg(reg)

    def drop_tmp_regs(self, regs: List[QReg]):
        for reg in regs:
            self.drop_tmp_reg(reg)

    def get_tmp_srcs(self, srcs: List[QReg]) -> List[QReg]:
        tmp_srcs: List[QReg] = []
        for src in srcs:
            if src.tmp:
                tmp_srcs.append(src)
        return tmp_srcs

    def get_max_tmp_src(self, srcs: List[QReg]) -> Union[QReg, None]:
        tmp_srcs = self.get_tmp_srcs(srcs)
        return self.get_max_reg(tmp_srcs)

    def get_min_tmp_src(self, srcs: List[QReg]) -> QReg:
        tmp_srcs = self.get_tmp_srcs(srcs)
        return self.get_min_reg(tmp_srcs)

    def get_max_reg(self, regs: List[QReg]) -> Union[QReg, None]:
        if len(regs) == 0:
            return None
        else:
            return max(regs, key=len)

    def get_min_reg(self, regs: List[QReg]) -> Union[QReg, None]:
        if len(regs) == 0:
            return None
        else:
            return min(regs, key=len)

    def assemble_to_bool(self, src: QReg, prev: Qubit = None) -> Qubit:
        trg = self.get_bit()

        all_src_bits: List[Qubit] = []
        for bit in src:
            all_src_bits.append(bit)

        if prev:
            all_src_bits.append(prev)

        print(all_src_bits)
        print(trg)

        # all_src_bits = set(all_src_bits).

        self.qc.x(all_src_bits)
        self.qc.x(trg)
        self.qc.mcx(all_src_bits, trg)
        self.qc.x(all_src_bits)

        self.qc.barrier()

        return trg

    def x(self, trg):
        if self.check_cond and len(self.conditions):
            cond = self.conditions.pop()
            self.qc.cx(cond, trg)
            self.conditions.append(cond)
        else:
            self.qc.x(trg)

    def cx(self, src, trg):
        if self.check_cond and len(self.conditions):
            cond = self.conditions.pop()
            self.qc.ccx(src, cond, trg)
            self.conditions.append(cond)
        else:
            self.qc.cx(src, trg)

    def mcx(self, srcs, trg):
        if self.check_cond and len(self.conditions):
            cond = self.conditions.pop()
            srcs = srcs.copy()
            srcs.append(cond)
            self.qc.mcx(srcs, trg)
            self.conditions.append(cond)
        else:
            self.qc.mcx(srcs, trg)

    def swap(self, trg1, trg2):
        if self.check_cond and len(self.conditions):
            cond = self.conditions.pop()
            self.qc.cswap(cond, trg1, trg2)
            self.conditions.append(cond)
        else:
            self.qc.swap(trg1, trg2)

    def assemble_invert(self, src: QReg) -> QReg:
        if src.tmp:
            src.tmp = False
            self.x(src)
            return src
        else:
            trg = self.create_reg(len(src))
            self.x(trg)
            for i in range(len(src)):
                self.cx(src[i], trg[i])
            return trg

    def assemble_xor(self, srcs: List[QReg]) -> QReg:
        max_tmp_src = self.get_max_tmp_src(srcs)
        if max_tmp_src:
            trg = self.resize_reg(max_tmp_src, len(self.get_max_reg(srcs)))
            srcs.remove(max_tmp_src)
        else:
            trg = self.create_reg(len(self.get_max_reg(srcs)))
            pass

        for src in srcs:
            for i in range(min(len(src), len(trg))):
                self.cx(src[i], trg[i])
                pass

        return trg

    def assemble_bit_and(self, srcs: List[QReg]) -> QReg:
        min_tmp_src = self.get_min_tmp_src(srcs)
        if min_tmp_src:
            trg = self.resize_reg(min_tmp_src, len(self.get_min_reg(srcs)))
            srcs.remove(min_tmp_src)

            for i in range(len(trg)):
                srcs_bits: List[Qubit] = []
                for src in srcs:
                    srcs_bits.append(src[i])

                tmp_bit = self.get_bit()
                self.swap(trg[i], tmp_bit)
                srcs_bits.append(tmp_bit)

                self.mcx(srcs_bits, trg[i])

                self.drop_bit(tmp_bit)
        else:
            trg = self.create_reg(len(self.get_min_reg(srcs)))

            for i in range(len(trg)):
                srcs_bits: List[Qubit] = []
                for src in srcs:
                    srcs_bits.append(src[i])

                self.mcx(srcs_bits, trg[i])

        return trg

    # TODO: refactor so srcs_bits will be created once
    def assemble_bit_or(self, srcs: List[QReg]) -> QReg:
        max_tmp_src = self.get_max_tmp_src(srcs)
        if max_tmp_src:
            trg = self.resize_reg(max_tmp_src, len(self.get_max_reg(srcs)))
            srcs.remove(max_tmp_src)

            for i in range(len(trg)):
                srcs_bits: List[Qubit] = []
                for src in srcs:

                    srcs_bits.append(src[i])

                tmp_bit = self.get_bit()
                self.swap(trg[i], tmp_bit)
                srcs_bits.append(tmp_bit)

                self.x(srcs_bits)
                self.x(trg[i])
                self.mcx(srcs_bits, trg[i])

                srcs_bits.remove(tmp_bit)
                self.x(srcs_bits)

                self.drop_bit(tmp_bit)
        else:
            trg = self.create_reg(len(self.get_max_reg(srcs)))

            for i in range(len(trg)):
                srcs_bits: List[Qubit] = []
                for src in srcs:
                    if len(src) > i:
                        srcs_bits.append(src[i])

                self.x(srcs_bits)
                self.x(trg[i])
                self.mcx(srcs_bits, trg[i])
                self.x(srcs_bits)

        return trg


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

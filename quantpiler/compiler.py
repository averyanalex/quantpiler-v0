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

from . import utils
from .qreg import QReg


def get_args_vars(func: Callable) -> Dict[str, int]:
    args_vars: Dict[str, int] = {}

    st = get_ast(func)
    args = st.body[0].args.args
    for arg in args:
        args_vars[arg.arg] = arg.annotation.value

    return args_vars


def get_return_size(func: Callable) -> int:
    """Get the return size of the quantum function.

    Args:
        func (Callable): Quantum function.

    Returns:
        int: 0 if the function returns nothing, otherwise the return size.
    """
    st = get_ast(func)
    try:
        return st.body[0].returns.value
    except AttributeError:
        return 0


def get_ast(module) -> ast.AST:
    """Get the AST of the python module.

    Args:
        module: Python module.

    Returns:
        ast.AST: The resulting AST.
    """
    source = inspect.getsource(module)
    source = textwrap.dedent(source)
    return ast.parse(source)


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


def get_tmp_regs(regs: List[QReg]) -> List[QReg]:
    """Get all temporary registers from the given registers.

    Args:
        regs (List[QReg]): A list of registers in which to find temporary registers.

    Returns:
        List[QReg]: Temporary registers.
    """
    return [src for src in regs if src.tmp]


def get_max_tmp_src(srcs: List[QReg]) -> Union[QReg, None]:
    tmp_srcs = get_tmp_regs(srcs)
    return get_max_reg(tmp_srcs)


def get_min_tmp_src(srcs: List[QReg]) -> QReg:
    tmp_srcs = get_tmp_regs(srcs)
    return get_min_reg(tmp_srcs)


def get_max_reg(regs: List[QReg]) -> Union[QReg, None]:
    """Get the register with the maximum size.

    Args:
        regs (List[QReg]): Registers.

    Returns:
        Union[QReg, None]: The largest register if the regs is not empty and None otherwise.
    """
    if regs:
        return max(regs, key=len)
    else:
        return None


def get_min_reg(regs: List[QReg]) -> Union[QReg, None]:
    """Get the register with the minimum size.

    Args:
        regs (List[QReg]): Registers.

    Returns:
        Union[QReg, None]: The smallest register if the regs is not empty and None otherwise.
    """
    if regs:
        return min(regs, key=len)
    else:
        return None


class Compiler:
    qc: QuantumCircuit = None
    # TODO: variables lifetime calculation
    variables: Dict[str, QReg] = {}
    arguments: Dict[str, QReg] = {}
    conditions: List[Qubit] = []
    ret: QReg = None
    bits: List[Qubit] = []
    add_barriers: bool = True

    def __init__(self):
        self.qc = None
        self.variables = {}
        self.arguments = {}
        self.conditions = []
        self.ret = None
        self.bits = []
        self.add_barriers = True

    def set_qc(self, qc: QuantumCircuit):
        self.qc = qc

    def assemble(self, func: Callable) -> QuantumCircuit:
        # Create quantum circuit
        self.qc = QuantumCircuit(name=func.__name__)

        # Create qreg for every function's argument
        args_vars = get_args_vars(func)
        for arg_name, arg_bitness in args_vars.items():
            self.arguments[arg_name] = self.create_reg(arg_bitness)

        self.variables = self.arguments.copy()

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

            target_var_name = instruction.targets[0].id

            # If we update variable value
            if target_var_name in self.variables:
                old_var = self.variables[target_var_name]

                if old_var not in self.arguments.values():
                    # If variable is not function argument,
                    # we will drop its original value
                    old_var.tmp = True

                new_var = self.assemble_op(instruction.value)

                if old_var not in self.arguments.values():
                    self.drop_unused_bits(new_var, old_var)

            # If we just defining new variable
            else:
                new_var = self.assemble_op(instruction.value)

            self.variables[target_var_name] = new_var

        elif inst_type == ast.AnnAssign:
            target_var_name = instruction.target

            # If we update variable value
            if target_var_name in self.variables:
                old_var = self.variables[target_var_name]

                if old_var not in self.arguments.values():
                    # If variable is not function argument,
                    # we will drop its original value
                    old_var.tmp = True

                new_var = self.assemble_op(
                    instruction.value, limit=instruction.annotation.value
                )

                if old_var not in self.arguments.values():
                    self.drop_unused_bits(new_var, old_var)

            # If we just defining new variable
            else:
                new_var = self.assemble_op(
                    instruction.value, limit=instruction.annotation.value
                )

            self.variables[target_var_name] = new_var

        elif inst_type == ast.Return:
            if type(instruction.value) == ast.Name:
                self.ret = self.variables[instruction.value.id]
            else:
                self.ret = self.assemble_op(instruction.value)

        elif inst_type == ast.If:
            self.assemble_if(instruction)

        else:
            raise NotImplementedError(f"Unsupported top-level operation: {inst_type}")

    def assemble_op(self, op: ast.AST, limit: int = float("inf")) -> QReg:
        op_type = type(op)
        if op_type == ast.Name:
            # TODO: check cond
            res = self.variables[op.id]

        elif op_type == ast.Call:
            # const loading
            res = self.reg_from_const(op.args[0].value)

        elif op_type == ast.UnaryOp:
            source = self.op_to_reg(op.operand)

            op_subtype = type(op.op)
            if op_subtype == ast.Invert:
                res = self.assemble_invert(source, limit=limit)
            else:
                raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")

            self.drop_tmp_reg(source)

        elif op_type == ast.BinOp:
            op_subtype = type(op.op)
            if op_subtype == ast.BitXor:
                sources = self.ops_to_regs(unwrap_ops_chain(op, ast.BitXor))
                res = self.assemble_xor(sources, limit=limit)
                self.drop_tmp_regs(sources)
            elif op_subtype == ast.BitAnd:
                sources = self.ops_to_regs(unwrap_ops_chain(op, ast.BitAnd))
                res = self.assemble_bit_and(sources, limit=limit)
                self.drop_tmp_regs(sources)
            elif op_subtype == ast.BitOr:
                sources = self.ops_to_regs(unwrap_ops_chain(op, ast.BitOr))
                res = self.assemble_bit_or(sources, limit=limit)
                self.drop_tmp_regs(sources)
            elif op_subtype == ast.LShift:
                source = self.op_to_reg(op.left)
                res = self.assemble_lshift(source, op.right.value, limit=limit)
                self.drop_tmp_reg(source)
            elif op_subtype == ast.RShift:
                source = self.op_to_reg(op.left)
                res = self.assemble_rshift(source, op.right.value, limit=limit)
                self.drop_tmp_reg(source)
            else:
                raise NotImplementedError(f"Unsupported op {op_subtype} of {op_type}")
        else:
            raise NotImplementedError(f"Unsupported operation: {op_type}")

        self.barrier()

        return res

    def assemble_if(self, inst: ast.If):
        """Assemble ast.If operation.

        Args:
            inst (ast.If): Operation to assemble.
        """
        test_res = self.assemble_op(inst.test)

        if self.conditions:
            # If there is already conditions: calculate (past and current)
            res_cond = self.assemble_to_bool(test_res, prev=self.conditions[-1])
            self.conditions.append(res_cond)
        else:
            # If is is first If op just add cond to conditions
            cur_cond = self.assemble_to_bool(test_res)
            self.conditions.append(cur_cond)

        # Drop reg with test result
        if type(inst.test) != ast.Name:
            self.destroy_reg(test_res)

        self.assemble_instructions(inst.body)

        # Else
        self.qc.x(self.conditions[-1])
        self.assemble_instructions(inst.orelse)

        last_cond = self.conditions.pop()
        self.drop_bit(last_cond)

    def op_to_reg(self, op: ast.AST) -> QReg:
        """Perform an operation and return the resulting register.

        Args:
            op (ast.AST): AST operation to execute.

        Returns:
            QReg: Resulting register.
        """
        if type(op) == ast.Name:
            return self.variables[op.id]
        else:
            reg = self.assemble_op(op)
            reg.tmp = True
            return reg

    def ops_to_regs(self, ops: List[ast.AST]) -> List[QReg]:
        """Perform all operations and return a list of registers.

        Args:
            ops (List[ast.AST]): List of AST operations to execute.

        Returns:
            List[QReg]: List of resulting registers.
        """
        return list(map(self.op_to_reg, ops))

    def create_bit(self) -> Qubit:
        """Create qubit and add it to QuantumCircuit.

        Returns:
            Qubit: The created qubit.
        """
        reg = QuantumRegister(1)
        self.qc.add_register(reg)
        return reg[0]

    def get_bit(self) -> Qubit:
        """Return qubit in 0 state.

        If an unused qubit exists, it will be returned, otherwise a new one will be created.

        Returns:
            Qubit: Qubit in 0 state.
        """
        if self.bits:
            bit = self.bits.pop()
            self.qc.reset(bit)
        else:
            bit = self.create_bit()
        return bit

    def drop_bit(self, bit: Qubit):
        """Add a qubit to the stack of unused qubits.

        Args:
            bit (Qubit): Unused qubit.
        """
        self.bits.append(bit)

    def drop_unused_bits(self, used_reg: QReg, unused_reg: QReg):
        """Drop qubits that are in unused_reg but not in used_reg.

        Args:
            used_reg (QReg): Register in use.
            unused_reg (QReg): Unused register.
        """
        for unused_bit in unused_reg:
            if unused_bit not in used_reg:
                self.drop_bit(unused_bit)

    def create_reg(self, size: int) -> QReg:
        """Create register of given size.

        Args:
            size (int): Number of qubits in the register.

        Returns:
            QReg: Created register.
        """
        bits = [self.get_bit() for _ in range(size)]
        return QReg(bits=bits)

    def reg_from_const(self, data: int) -> QReg:
        """Create a register with the specified number.

        Args:
            data (int): Register value.

        Returns:
            QReg: Register with the specified number.
        """
        data_bits = utils.uint_to_bits(data)
        data_bits.reverse()
        reg = self.create_reg(len(data_bits))
        for reg_bit, data_bit in zip(reg, data_bits):
            if data_bit:
                self.x(reg_bit)
        return reg

    def destroy_reg(self, reg: QReg):
        for bit in reg:
            self.drop_bit(bit)

    def resize_reg(self, reg: QReg, size: int) -> QReg:
        """Resize register.

        If the new size is larger than the current size, new qubits will be added to the end of the register.
        If not, the extra qubits at the end of register will be removed.

        Args:
            reg (QReg): Register to resize.
            size (int): The new register size.

        Raises:
            ValueError: Invalid arguments.

        Returns:
            QReg: The resized register.
        """
        if size <= 0:
            raise ValueError("Size of register can't be 0 or lower.")

        bits = list(reg)

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
        """Drop a register if it is temporary.

        Args:
            reg (QReg): Register to check and drop.
        """
        if reg.tmp:
            self.destroy_reg(reg)

    def drop_tmp_regs(self, regs: List[QReg]):
        for reg in regs:
            self.drop_tmp_reg(reg)

    def assemble_to_bool(self, src: QReg, prev: Qubit = None) -> Qubit:
        if len(src) > 1:
            trg = self.get_bit()

            all_src_bits = list(src)

            if prev:
                all_src_bits.append(prev)

            self.qc.x(all_src_bits)
            self.qc.x(trg)
            self.qc.mcx(all_src_bits, trg)
            self.qc.x(all_src_bits)

            self.barrier()

            return trg
        else:
            return src[0]

    def barrier(self):
        """Adds a barrier to the circuit if they are enabled."""
        if self.add_barriers:
            self.qc.barrier()

    def x(self, trg):
        if len(self.conditions):
            cond = self.conditions.pop()
            self.qc.cx(cond, trg)
            self.conditions.append(cond)
        else:
            self.qc.x(trg)

    def cx(self, src, trg):
        if len(self.conditions):
            cond = self.conditions.pop()
            self.qc.ccx(src, cond, trg)
            self.conditions.append(cond)
        else:
            self.qc.cx(src, trg)

    def mcx(self, srcs, trg):
        if len(self.conditions):
            cond = self.conditions.pop()
            srcs = srcs.copy()
            srcs.append(cond)
            self.qc.mcx(srcs, trg)
            self.conditions.append(cond)
        else:
            self.qc.mcx(srcs, trg)

    def swap(self, trg1, trg2):
        if len(self.conditions):
            cond = self.conditions.pop()
            self.qc.cswap(cond, trg1, trg2)
            self.conditions.append(cond)
        else:
            self.qc.swap(trg1, trg2)

    def assemble_copy(self, src: QReg, trg: Union[None, QReg] = None) -> QReg:
        if trg:
            for i in range(min(len(src), len(trg))):
                if src[i] != trg[i]:
                    self.cx(src[i], trg[i])
        else:
            trg = self.create_reg(len(src))
            for i in range(len(src)):
                if src[i] != trg[i]:
                    self.cx(src[i], trg[i])

        return trg

    def assemble_invert(self, src: QReg, limit: int = float("inf")) -> QReg:
        """Invert register.

        This will flip all the qubits in the register.

        Args:
            src (QReg): Register to invert.
            limit (int, optional): Result size limit. Defaults to float("inf").

        Returns:
            QReg: Inverted register.
        """
        if src.tmp:
            src.tmp = False
            if limit >= len(src):
                self.x(src)
            else:
                src = self.resize_reg(src, limit)
                self.x(src)
            return src
        else:
            trg = self.create_reg(min(len(src), limit))
            self.x(trg)
            for src_bit, trg_bit in zip(src, trg):
                self.cx(src_bit, trg_bit)
            return trg

    def assemble_xor(self, srcs: List[QReg], limit: int = float("inf")) -> QReg:
        """Calculate XOR of registers.

        Args:
            srcs (List[QReg]): List of input registers.
            limit (int, optional): Result size limit. Defaults to float("inf").

        Returns:
            QReg: Register with result.
        """
        limit = min(limit, len(get_max_reg(srcs)))

        max_tmp_src = get_max_tmp_src(srcs)
        if max_tmp_src:
            trg = self.resize_reg(max_tmp_src, limit)
            trg.tmp = False
            srcs.remove(max_tmp_src)
        else:
            trg = self.create_reg(limit)

        for src in srcs:
            for src_bit, trg_bit in zip(src, trg):
                self.cx(src_bit, trg_bit)

        return trg

    def assemble_bit_and(self, srcs: List[QReg], limit: int = float("inf")) -> QReg:
        """Calculate AND of registers.

        Args:
            srcs (List[QReg]): List of input registers.
            limit (int, optional): Result size limit. Defaults to float("inf").

        Returns:
            QReg: Register with result.
        """
        limit = min(limit, len(get_min_reg(srcs)))

        min_tmp_src = get_min_tmp_src(srcs)
        if min_tmp_src:
            trg = self.resize_reg(min_tmp_src, limit)
            trg.tmp = False
            srcs.remove(min_tmp_src)

            for i in range(limit):
                srcs_bits = [src[i] for src in srcs]

                tmp_bit = self.get_bit()
                self.swap(trg[i], tmp_bit)
                srcs_bits.append(tmp_bit)

                self.mcx(srcs_bits, trg[i])

                self.drop_bit(tmp_bit)
        else:
            trg = self.create_reg(limit)

            for i in range(limit):
                srcs_bits = [src[i] for src in srcs]

                self.mcx(srcs_bits, trg[i])

        return trg

    # TODO: refactor so srcs_bits will be created once
    def assemble_bit_or(self, srcs: List[QReg], limit: int = float("inf")) -> QReg:
        """Calculate OR of registers.

        Args:
            srcs (List[QReg]): List of input registers.
            limit (int, optional): Result size limit. Defaults to float("inf").

        Returns:
            QReg: Register with result.
        """
        limit = min(limit, len(get_max_reg(srcs)))

        max_tmp_src = get_max_tmp_src(srcs)
        if max_tmp_src:
            trg = self.resize_reg(max_tmp_src, limit)
            trg.tmp = False
            srcs.remove(max_tmp_src)

            for i in range(limit):
                srcs_bits = [src[i] for src in srcs]

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
            trg = self.create_reg(limit)

            for i in range(limit):
                srcs_bits = [src[i] for src in srcs]

                self.x(srcs_bits)
                self.x(trg[i])
                self.mcx(srcs_bits, trg[i])
                self.x(srcs_bits)

        return trg

    def assemble_lshift(
        self, src: QReg, distance: int, limit: int = float("inf")
    ) -> QReg:
        """Calculate LShift of register.

        Add distance bits at the beginng and drop bits over limit at the end.

        Args:
            src (QReg): Input register.
            distance (int): Shift distance.
            limit (int, optional): Result size limit. Defaults to float("inf").

        Returns:
            QReg: Register with result.
        """
        limit = min(limit, len(src) + distance)

        if src.tmp:
            src.tmp = False
            bits = list(src)

            # Add new bits to the beginning
            for _ in range(distance):
                bits.insert(0, self.get_bit())

            # Drop bits at the end
            for _ in range(len(bits) - limit):
                self.drop_bit(bits.pop())

            res = QReg(bits=bits)
        else:
            res = self.create_reg(limit)
            for i in range(limit - distance):
                self.cx(src[i], res[i + distance])

        return res

    def assemble_rshift(
        self, src: QReg, distance: int, limit: int = float("inf")
    ) -> QReg:
        """Calculate RShift of register.

        Args:
            src (QReg): Input register.
            distance (int): Shift distance.
            limit (int, optional): Result size limit. Defaults to float("inf").

        Returns:
            QReg: Register with result.
        """
        limit = min(len(src) - distance, limit)

        if src.tmp:
            src.tmp = False
            bits = list(src)

            for _ in range(distance):
                self.drop_bit(bits.pop(0))

            for _ in range(len(bits) - limit):
                self.drop_bit(bits.pop())

            res = QReg(bits=bits)
        else:
            res = self.create_reg(limit)
            for i in range(limit):
                self.cx(src[i + distance], res[i])

        return res

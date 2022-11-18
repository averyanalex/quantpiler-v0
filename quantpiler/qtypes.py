from typing import List, Union
from functools import total_ordering

from .utils import int_to_bits, bits_to_int, get_int_len


@total_ordering
class Qvar:
    tp: str = "bool"
    value: List[bool] = [False]

    def __init__(self, tp: str, size: int, number: Union[int, bool]):
        self.set_type(tp)
        self.set_size(size)
        self.set_num(number)

    def set_type(self, tp: str):
        if not tp in ["bool", "uint", "int"]:
            raise NotImplementedError()

        self.tp = tp
        raise NotImplementedError()

    def get_type(self) -> str:
        return self.tp

    def set_size(self, length: int):
        if length < 1:
            raise NotImplementedError()

        if length > 1 and self.tp == "bool":
            raise NotImplementedError()

        if len(self) > length:
            for _ in range(length - len(self)):
                self.value.append(False)
        elif len(self) < length:
            for _ in range(len(self) - length):
                self.value.pop()

    def __len__(self) -> int:
        return len(self.value)

    def set_value(self, value: List[bool]):
        self.set_size(len(value))
        self.value = value

    def get_value(self) -> List[bool]:
        return self.value

    def set_uint(self, number: int):
        self.set_value(uint_to_bits(number, bits=len(self))[::-1])

    def get_uint(self) -> int:
        return bits_to_uint(self.get_value()[::-1])

    def set_int(self, number: int):
        raise NotImplementedError()

    def get_int(self) -> int:
        return bits_to_int(self.get_value()[::-1])

    def set_bool(self, number: bool):
        if number:
            self.set_value([True])
        else:
            self.set_value([False])

    def get_bool(self) -> bool:
        for v in self.get_value():
            if v:
                return True
        return False

    def set_num(self, number: Union[int, bool]):
        t = self.get_type()
        if t == "bool":
            self.set_bool(number)
        elif t == "uint":
            self.set_uint(number)
        elif t == "int":
            self.set_int(number)
        else:
            raise NotImplementedError()

    def get_num(self) -> int:
        t = self.get_type()
        if t == "bool":
            if self.get_bool():
                return 1
            else:
                return 0
        elif t == "uint":
            return self.get_uint()
        elif t == "int":
            return self.get_int()
        else:
            raise NotImplementedError()

    def __eq__(self, other):
        return self.get_num() == other.get_num()

    def __lt__(self, other):
        return self.get_num() < other.get_num()

    def __invert__(self):
        new_value = []
        for v in self.value:
            if v:
                new_value.append(False)
            else:
                new_value.append(True)

        new = Qvar(self.get_type(), len(self), 0)
        new.set_value(new_value)
        return new

    def __add__(self, other):
        res = self.get_num() + other.get_num()
        bits = max(len(self), len(other)) + 1
        if "uint" in [self.get_type(), other.get_type()]:
            tp = "uint"
        else:
            tp = "int"
        return Qvar(tp, bits, res)

    def __sub__(self, other):
        res = self.get_num() - other.get_num()
        bits = max(len(self), len(other)) + 1
        return Qvar("uint", bits, res)

    def __and__(self, other):
        bits = min(len(self), len(other))

        new_value = []
        for i in range(bits):
            new_value.append(self.get_value()[i] and other.get_value()[i])

        new = Qvar(self.get_type(), bits, 0)
        new.set_value(new_value)
        return new


def new_quint(number: int, bits=None) -> Quint:
    if not bits:
        bits = get_uint_len(number)
    q = Quint(bits)
    q.set_uint(number)
    return q


def new_quint_val(value: List[bool]) -> Quint:
    q = Quint(len(value))
    q.value = value
    return q

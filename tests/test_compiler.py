from quantpiler import compiler

from quantpiler.utils import execute_qc_once


def test_or():
    def or_func(a, b, c):
        a = True
        c = a | b

    qc = compiler.compile(or_func, 0)
    bits = execute_qc_once(qc)
    assert bits == "101"


def test_complex():
    def complex_func(a, b, c, d):
        a = True
        not_a = not a
        b = not not_a
        a_or_d = a | d
        c = b & (a_or_d | (d == a))
        d = (c != False) & b == True
        b = a | d

    qc = compiler.compile(complex_func, 5)
    bits = execute_qc_once(qc)
    assert bits[-4:] == "1111"

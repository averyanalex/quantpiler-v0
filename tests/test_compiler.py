from quantpiler import compiler

from qiskit import BasicAer, execute
qasm_sim = BasicAer.get_backend('qasm_simulator')


def compile_execute(func, ancillas):
    qc = compiler.compile(func, ancillas)
    qc.measure_all()
    results = execute(qc, backend=qasm_sim, shots=1).result()

    answer = results.get_counts()
    bits = list(answer.keys())[0]

    return bits


def test_or():
    def or_func(a, b, c):
        a = True
        c = a | b

    bits = compile_execute(or_func, 0)
    assert bits == '101'


def test_complex():
    def complex_func(a, b, c, d):
        a = True
        not_a = not a
        b = not not_a
        a_or_d = a | d
        c = b & (a_or_d | (d == a))
        d = (c != False) & b == True
        b = a | d

    bits = compile_execute(complex_func, 5)
    assert bits[-4:] == '1111'

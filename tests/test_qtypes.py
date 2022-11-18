from quantpiler.qtypes import QInt, new_qint, new_qint_val


def test_set_int():
    a = QInt(4)
    a.set_int(-2)
    assert a.value == [0, 1, 1, 1]

    a = QInt(4)
    a.set_int(2)
    assert a.value == [0, 1, 0, 0]

    a = QInt(4)
    a.set_int(0)
    assert a.value == [0, 0, 0, 0]


def test_get_int():
    for i in range(-15, 16):
        a = QInt(5)
        a.set_int(i)
        assert a.get_int() == i


def test_eq():
    a = QInt(4)
    b = QInt(4)
    assert a == b

    a = QInt(2)
    b = QInt(4)
    assert a == b

    a = QInt(2)
    a.set_int(1)
    b = QInt(2)
    b.set_int(1)
    assert a == b

    a = QInt(2)
    a.set_int(1)
    b = QInt(2)
    assert a != b


def test_gt():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert (new_qint(a) > new_qint(b)) == (a > b)


def test_ge():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert (new_qint(a) >= new_qint(b)) == (a >= b)


def test_lt():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert (new_qint(a) < new_qint(b)) == (a < b)


def test_le():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert (new_qint(a) <= new_qint(b)) == (a <= b)


def test_invert():
    for i in range(-15, 16):
        q = new_qint(i)
        assert ~i == (~q).get_int()
        assert i == q.get_int()


def test_add():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert (new_qint(a) + new_qint(b)).get_int() == (a + b)


def test_sub():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert (new_qint(a) - new_qint(b)).get_int() == (a - b)


def test_and():
    a = new_qint_val([1, 1, 0])
    b = new_qint_val([1, 0, 1, 1])
    assert (a & b).value == [1, 0, 0]

    a = new_qint_val([1, 1, 1])
    b = new_qint_val([0, 0, 1, 0])
    assert (a & b).value == [0, 0, 1]

from quantpiler import utils


def test_int_to_bits():
    bl = utils.int_to_bits(17, bits=7)
    assert bl == [0, 0, 1, 0, 0, 0, 1]

    bl = utils.int_to_bits(-1, bits=4)
    assert bl == [1, 1, 1, 1]

    bl = utils.int_to_bits(-2, bits=4)
    assert bl == [1, 1, 1, 0]


def test_bits_to_int():
    assert utils.bits_to_int([0, 0, 1, 0, 0, 0, 1]) == 17
    assert utils.bits_to_int([0, 1, 0, 0, 0, 1]) == 17
    assert utils.bits_to_int([1, 1, 1, 1]) == -1
    assert utils.bits_to_int([1, 1, 1, 0]) == -2
    assert utils.bits_to_int([1, 0, 1, 1]) == -5

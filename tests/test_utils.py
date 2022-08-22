from quantpiler import utils


def test_int_to_bits():
    bl = utils.int_to_bits(17, bits=7)
    assert bl == [0, 0, 1, 0, 0, 0, 1]

    bl = utils.int_to_bits(17)
    assert bl == [1, 0, 0, 0, 1]

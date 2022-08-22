from quantpiler import utils


def test_int_to_bits():
    bl = utils.int_to_bits(17, 5)
    assert bl == [1, 0, 0, 0, 1]

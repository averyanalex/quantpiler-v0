[![License](https://img.shields.io/github/license/averyanalex/quantpiler.svg?)](https://opensource.org/licenses/Apache-2.0)
[![Publish status](https://github.com/averyanalex/quantpiler/actions/workflows/publish.yml/badge.svg)](https://github.com/averyanalex/quantpiler/actions/workflows/publish.yml)
[![Latest release](https://img.shields.io/github/tag/averyanalex/quantpiler.svg)](https://github.com/averyanalex/quantpiler/tags)
[![Downloads](https://pepy.tech/badge/quantpiler)](https://pypi.org/project/quantpiler/)

# Quantpiler

This library can generate some common circuits and compile python functions to circuits

## Examples:

### Compile:

```python
from quantpiler.compiler import compile

def example_func(a, b):
    a = True
    a_or_b = a | b
    tmp = a & (a_or_b | (a == b))
    b = tmp != False

qc = compile(example_func, 4)
qc.draw(output="mpl")
```

![Compiled circuit](https://raw.githubusercontent.com/averyanalex/quantpiler/397073274ea07ad9d3f85345cf15823ed79813f0/images/compiler.png)

### qRAM

```python
from quantpiler.qram import new_qram

values = {0: 1, 1: 3, 2: 6, 3: 7}
qram = new_qram(2, 3, values)

qram.draw(output="mpl")
```

![qRAM circuit](https://raw.githubusercontent.com/averyanalex/quantpiler/397073274ea07ad9d3f85345cf15823ed79813f0/images/qram.png)

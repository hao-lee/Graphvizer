When loading plugin, I encounter an `ImportError`:

```
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\syntaxchecker.py", line 6, in <module>
    from antlr4 import *
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\__init__.py", line 5, in <module>
    from antlr4.CommonTokenStream import CommonTokenStream
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\CommonTokenStream.py", line 33, in <module>
    from antlr4.Lexer import Lexer
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\Lexer.py", line 12, in <module>
    from typing.io import TextIO
ImportError: No module named 'typing.io'
```

So I copy `D:\Python\Python35\Lib\typing.py` to a subdirectory `Lib\` in plugin directory and add its absolute path to `sys.path`, but another error occurs when reopening sublime:

```
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\syntaxchecker.py", line 7, in <module>
    from antlr4 import *
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\__init__.py", line 5, in <module>
    from antlr4.CommonTokenStream import CommonTokenStream
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\CommonTokenStream.py", line 33, in <module>
    from antlr4.Lexer import Lexer
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\Lexer.py", line 15, in <module>
    from antlr4.atn.LexerATNSimulator import LexerATNSimulator
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\atn\LexerATNSimulator.py", line 23, in <module>
    from antlr4.PredictionContext import PredictionContextCache, SingletonPredictionContext, PredictionContext
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\PredictionContext.py", line 11, in <module>
    from antlr4.atn.ATN import ATN
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\atn\ATN.py", line 10, in <module>
    from antlr4.atn.ATNType import ATNType
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\atn\ATNType.py", line 6, in <module>
    from enum import IntEnum
ImportError: No module named 'enum'
```

I then copy `D:\Python\Python35\Lib\enum.py` into `Lib\` and reopen sublime. This time I encounter a new error:

```
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\syntaxchecker.py", line 7, in <module>
    from antlr4 import *
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\__init__.py", line 5, in <module>
    from antlr4.CommonTokenStream import CommonTokenStream
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\CommonTokenStream.py", line 33, in <module>
    from antlr4.Lexer import Lexer
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\Lexer.py", line 15, in <module>
    from antlr4.atn.LexerATNSimulator import LexerATNSimulator
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\atn\LexerATNSimulator.py", line 23, in <module>
    from antlr4.PredictionContext import PredictionContextCache, SingletonPredictionContext, PredictionContext
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\PredictionContext.py", line 11, in <module>
    from antlr4.atn.ATN import ATN
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\atn\ATN.py", line 10, in <module>
    from antlr4.atn.ATNType import ATNType
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\antlr4\atn\ATNType.py", line 6, in <module>
    from enum import IntEnum
  File "D:\Sublime Text 3\Data\Packages\Graphvizer\Lib\enum.py", line 2, in <module>
    from types import MappingProxyType, DynamicClassAttribute
ImportError: cannot import name DynamicClassAttribute
```

I copy `types.py` file into `Lib\`, but the error message is the same as above.

At last, I search `python DynamicClassAttribute` on Google to find out what the hell and I see [this page](https://docs.python.org/3/library/types.html). Then I know the `DynamicClassAttribute` is a new feature of Python 3.4, while Sublime Text 3 uses Python 3.3 as its internal interpreter. I must find a way to address this problem. At this time, the [next search result](https://gist.github.com/med-merchise/1aba8c66045b104ec419b58451286868) catch my eye. In this article I learn a new term - `back-porting`. So I search `python enum backport` on Google and find a package called [`enum34 1.1.6`](https://pypi.python.org/pypi/enum34) which is Python 3.4 Enum backported to 3.3, 3.2, 3.1, 2.7, 2.6, 2.5, and 2.4. Then I search `python typing3.4 backport` again and find a package called [`typing 3.5.2`](https://pypi.python.org/pypi/typing/3.5.2) which is a backport of the standard library typing module to Python versions older than 3.5. I download these two packages and put their directories into my plugin's directory and then add them to `sys.path`. Boom! All errors are solved!
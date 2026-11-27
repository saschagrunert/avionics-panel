"""The simulator's RPN for the tests (tests/test_mobiflight.py, tests/test_ifr1.py): a code's tokens, what it sets, a
run of it on given variables, and the checks every generated code passes: well_formed() and every_path()."""
import itertools
import math
import re

# a code's tokens: a variable, read as (A:NAME:INDEX, unit), (L:NAME, unit), (E:NAME, unit) (an environment variable,
# as the sim's clock) or (B:NAME) (an input event's value), or set as (>X:NAME) or (>A:NAME:INDEX, unit), a number or
# an operator. An L: name is letters, digits and _, or one an aircraft names otherwise (L_NAME: the COWS DA40's
# standby altimeter, aircraft.py).
TOKEN = re.compile(r"\([^()]*\)|[^\s()]+")
L_NAME = r"L:[A-Za-z0-9_]+|L:KOHLSMAN SETTING HG:2"
READ = re.compile(r"\((?:(?:A:([A-Z0-9 ]+(?::[1-9])?)|(" + L_NAME + r")), [A-Za-z][A-Za-z0-9 ]*|(B:[A-Z0-9_]+)|"
                  r"(E:[A-Z ]+), [A-Za-z][A-Za-z0-9 ]*)\)")
WRITE = re.compile(r"\(>(?:(K:(?:2:)?[A-Z0-9_]+|H:[A-Za-z0-9_-]+|" + L_NAME + r"|B:[A-Za-z0-9_]+_(?:Set|Toggle))|"
                   r"(A:[A-Z ]+:[1-9]), Enum)\)")
REGISTER = re.compile(r"(sp|s|l)([0-9])")         # a register: store and pop, store, load
NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?|0x[0-9A-F]+")
VALUE = re.compile(NUMBER.pattern + r"|[-+!<>%*/]|==|and|or|neg|abs|min|max|dnor|near|flr|if\{|els\{|\}|" +
                   REGISTER.pattern)


def sets(token):
    """What a token sets, as K:EVENT, H:EVENT, L:VARIABLE or A:VARIABLE:INDEX, or None"""
    write = WRITE.fullmatch(token)
    return write and (write[1] or write[2])


def run(code, variables=(), branches=None, default=None):
    """Runs a code as the simulator's RPN does, on these variables ({name: value}, an L: variable with its prefix):
    [(what it set, value)], with None for an event sent without a value. An L: variable it sets reads as set after that,
    and a B: input event's value as its _Set event sets it; a read in any unit gives the value as given (the simulator
    converts no L: variable to Bco16: parts.squawk() packs the code itself). Registers keep values for the code: sN
    keeps the top of the stack in N, spN takes it there, lN puts it back. branches: an iterator of bools that decides
    each if{ in place of the value it takes off the stack (every_path()); default: the value of a variable not in
    variables (None: a KeyError)."""
    variables, stack, out, registers = dict(variables), [], [], {}
    binary = {"+": lambda x, y: x + y, "-": lambda x, y: x - y, "%": lambda x, y: x % y, "*": lambda x, y: x * y,
              "/": lambda x, y: x / y, ">": lambda x, y: x > y, "<": lambda x, y: x < y,
              "==": lambda x, y: x == y, "and": lambda x, y: bool(x and y), "or": lambda x, y: bool(x or y),
              "min": min, "max": max}
    # near rounds half up, as the SDK's RPN page says (Python's round() goes to the even number)
    unary = {"!": lambda x: not x, "near": lambda x: math.floor(x + 0.5), "dnor": lambda x: x % 360, "abs": abs,
             "neg": lambda x: -x, "flr": math.floor}

    def block(tokens, live):
        """Runs the tokens up to the } that closes their block, if live, and returns the ones after it"""
        while tokens and tokens[0] != "}":
            token, tokens = tokens[0], tokens[1:]
            if token == "if{":
                value = stack.pop() if live else None
                taken = live and (next(branches) if branches is not None else bool(value))
                tokens = block(tokens, taken)
                if tokens[:1] == ["els{"]:
                    tokens = block(tokens[1:], live and not taken)
            elif not live:
                continue
            elif READ.fullmatch(token):
                read = READ.fullmatch(token)
                name = read[1] or read[2] or read[3] or read[4]
                value = variables[name] if default is None or name in variables else default
                stack.append(value)
            elif REGISTER.fullmatch(token):
                op, n = REGISTER.fullmatch(token).groups()
                if op == "l":
                    stack.append(registers[n])
                else:
                    registers[n] = stack.pop() if op == "sp" else stack[-1]
            elif sets(token):
                name = sets(token)
                # an event (an input event's _Toggle too) may go without a value; a variable takes one, which an
                # empty stack would leave unset
                assert stack or name.startswith(("K:", "H:")) or (name.startswith("B:") and name.endswith("_Toggle")), (
                    f"{name} set from an empty stack", code)
                value = stack.pop() if stack else None
                if name.startswith("K:2:"):
                    name, value = f"K:{name[4:]}", (value, stack.pop())
                out.append((name, value))
                name = out[-1][0]
                if name.startswith("L:"):                # an L: variable reads as set from then on
                    variables[name] = out[-1][1]
                elif name.startswith("B:"):
                    variables[name.removesuffix("_Set")] = out[-1][1]
            elif token in binary:
                right = stack.pop()
                stack.append(binary[token](stack.pop(), right))
            elif token in unary:
                stack.append(unary[token](stack.pop()))
            else:
                stack.append(float(token) if "." in token else int(token, 0))
        return tokens[1:]

    block(TOKEN.findall(code), True)
    assert not stack, code
    return out


def well_formed(code):
    """Asserts a code is one MobiFlight takes: every token reads a variable, sets an event or variable, or is a
    number or operator, every block is closed, and it sets something; no "@", which MobiFlight would replace with
    the button's value; and it fits the 1024 bytes of the message MobiFlight's WASM module takes it in
    (MOBIFLIGHT_MESSAGE_SIZE in its Module.cpp), with room for the command in front of it"""
    tokens = TOKEN.findall(code)
    assert " ".join(tokens) == code and "@" not in code, code
    assert len(code.encode()) < 1000, code
    depth = 0
    for token in tokens:
        assert READ.fullmatch(token) or sets(token) or VALUE.fullmatch(token), (token, code)
        depth += (token in ("if{", "els{")) - (token == "}")
        assert depth >= 0, code
    assert depth == 0 and any(sets(token) for token in tokens), code


def every_path(code):
    """Runs a code down each way its if{ blocks can go, every variable it reads 1 where a path needs no other, and
    asserts each leaves the stack empty, takes nothing off an empty one, sets no variable from an empty stack and loads
    no register that no store on it set: a branch no other test runs is checked too. A path that divides by 0 there
    cannot be told apart from one a real value never takes, and is passed over. Each if{ goes either way on its own,
    so a code that tests one condition twice fails on a path no value takes (a register stored under the first test
    and loaded under the second, say): write it so each path that loads a register stores it."""
    ifs = TOKEN.findall(code).count("if{")
    for way in itertools.product((True, False), repeat=ifs):
        try:
            run(code, branches=iter(way), default=1)
        except ZeroDivisionError:
            continue

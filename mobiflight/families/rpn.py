"""The statements the family tables write MobiFlight's calculator code with, in the simulator's RPN (MSFS 2024
SDK, Reverse Polish Notation). MobiFlight's WASM module runs a code as it is, with "@" replaced by the input's
value (MSFS2020CustomInputAction.cs), so no code holds one.

- k(): a key event of the SDK's Key Events pages, with its one parameter in front if it takes one;
- h(): an H: event, which the SDK's RPN page describes as going to an instrument's JavaScript only;
- b(): an input event of the aircraft's model behaviors, by its ID and the binding it calls (_Inc, _Dec, _PUSH,
  _TOGGLE), with the number of steps in front of an _Inc or _Dec, as the SDK's Input Event XML Properties call
  one: `1 (>B:Sound_COM1_Volume_Inc)`;
- lvar(): a local variable (L:) set to a value; names are case-insensitive (the SDK's register_named_variable);
- turn(): a step of so many degrees from a reading, rounded to whole degrees (near: the SDK's HEADING_BUG_SET
  takes whole ones) and wrapped to 0 to 360 (dnor), set with a key event that takes degrees (HEADING_BUG_SET,
  VOR1_SET, GPS_OBS_SET).
"""


def k(event, value=None):
    return f"(>K:{event})" if value is None else f"{value} (>K:{event})"


def h(event):
    return f"(>H:{event})"


def b(event, value=None):
    return f"(>B:{event})" if value is None else f"{value} (>B:{event})"


def lvar(variable, value):
    return f"{value} (>L:{variable})"


def turn(reading, event, degrees):
    return f"(A:{reading}, degrees) {abs(degrees)} {'+' if degrees > 0 else '-'} near dnor (>K:{event})"

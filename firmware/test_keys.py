"""Host tests for keys.py, the keyboard mode: the stored mode, the descriptor, the shortcuts and the report."""
import buttonmap as BM
import keys
import panel as P
import test_boot
from make_keys import shortcut_name

# HID usage IDs
F1, INSERT, HOME, PAGE_UP, DELETE, END, PAGE_DOWN = 0x3A, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E


def test_a_blank_or_unknown_byte_is_the_joystick_mode_and_unit_switches():
    nvm = bytearray(b"\xff" * 8)
    assert not keys.keyboard_mode(nvm) and nvm == b"\xff" * 8                  # blank flash: joysticks
    assert keys.keyboard_mode(nvm, toggle=True) and nvm[keys.MODE_BYTE] == keys.KEYBOARD
    assert keys.keyboard_mode(nvm) and keys.keyboard_mode(nvm)                  # kept
    assert not keys.keyboard_mode(nvm, toggle=True) and nvm == b"\xff" * 8
    for byte in (0x00, 0x4A, 0xA5):                                            # anything else: joysticks too
        nvm[keys.MODE_BYTE] = byte
        assert not keys.keyboard_mode(nvm) and nvm[keys.MODE_BYTE] == byte
        assert keys.keyboard_mode(nvm, toggle=True) and nvm[keys.MODE_BYTE] == keys.KEYBOARD


def test_the_start_pattern_is_three_turns():
    # SHIFT, UNIT, three times, 150 ms each (docs/using/keyboard.md)
    assert keys.START == (0, 1, 0, 1, 0, 1) and keys.BLINK_S == 0.15


def test_the_descriptor_is_the_boot_keyboards():
    # HID 1.11, appendix E.6, byte for byte: keys 0 to 101, no report ID
    e6 = bytes((0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01,
                0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01, 0x75, 0x08, 0x81, 0x01, 0x95, 0x05, 0x75, 0x01,
                0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x91, 0x02, 0x95, 0x01, 0x75, 0x03, 0x91, 0x01, 0x95, 0x06,
                0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xC0))
    assert e6 == keys.DESCRIPTOR and test_boot.hid_items(keys.DESCRIPTOR)[-1] == (0, 0xC, 0)


def every_shortcut():
    """{(device, name): (modifiers, key)}"""
    return {(dev, name): keys.shortcut(dev, b) for dev, names in BM.DEVICE.items() for b, name in enumerate(names)}


def owner(dev, name):
    """The button whose shortcut another one sends: SHIFT with a key without an amber legend, the key's plain one;
    in unit 2, everything but COM and NAV, unit 1's"""
    if dev == 2 and not (name.startswith(("COM_", "NAV_")) and name != "COM_121_5"):
        dev = 1
    return dev, name[2:] if name.startswith("S_") else name


def test_every_function_has_a_shortcut_of_its_own_and_the_rest_share_them():
    shortcuts = every_shortcut()
    owners = {owner(*k) for k in shortcuts}
    assert len(owners) == len(set(shortcuts.values())) == 114 and len(shortcuts) == 156
    for k, s in shortcuts.items():
        assert s == shortcuts[owner(*k)]
    assert {n for (d, n) in shortcuts if owner(d, n) == (d, n) and d == 2} == {
        "COM_SWAP", "NAV_SWAP", "COM_MHZ_UP", "COM_MHZ_DN", "COM_KHZ_UP", "COM_KHZ_DN", "NAV_MHZ_UP", "NAV_MHZ_DN",
        "NAV_KHZ_UP", "NAV_KHZ_DN"}


def test_the_shortcuts_keep_to_the_rules():
    # F1 to F12, Insert, Home, Page Up, Page Down and the arrows, all in the boot keyboard's range, each with at
    # least one modifier and never right Alt or the Windows keys; no Shift with a navigation key or arrow
    nav = {INSERT, HOME, PAGE_UP, PAGE_DOWN, 0x4F, 0x50, 0x51, 0x52}
    for mods, key in set(every_shortcut().values()):
        assert F1 <= key < F1 + 12 or key in nav
        assert mods and not mods & ~(keys.LC | keys.LS | keys.LA | keys.RC | keys.RS)
        assert key not in nav or not mods & (keys.LS | keys.RS)


# What a shortcut must not be, with a reason: MSFS 2024's default presets (they store left Ctrl, Shift and Alt),
# Windows, graphics drivers, overlays, and Linux, where the simulator's uhid keyboard reaches the desktop
EXACT = {(keys.LC, k): "autopilot" for k in list(range(F1, F1 + 12)) + [INSERT, HOME, PAGE_UP, PAGE_DOWN, DELETE, END]}
EXACT.update({(keys.LS, F1 + i): "cameras" for i in range(11)})
EXACT.update({(m, F1 + 3): "Alt+F4 closes" for m in (keys.LA, keys.LA | keys.LS, keys.LA | keys.RS)})
EXACT.update({(keys.LA, F1 + i): "NVIDIA, Medal, AMD" for i in (0, 1, 2, 6, 8, 9, 10, 11)})
EXACT.update({(m, F1 + 9): "NVIDIA replay, context menu" for m in (keys.LA | keys.RS, keys.LS, keys.RS)})
EXACT.update({(c | keys.LA, F1 + i): "Linux console, Intel" for c in (keys.LC, keys.RC) for i in range(12)})
EXACT.update({(c, F1 + 3): "Ctrl+F4 closes tabs" for c in (keys.LC, keys.RC)})
EXACT.update({(keys.LC | keys.LS, F1 + i): "2020 presets: mixture" for i in range(4)})


def test_no_shortcut_is_a_default_of_the_sim_or_a_system_shortcut():
    used = set(every_shortcut().values())
    assert not used & set(EXACT)
    # parts a shortcut may fire when unbound: never the menus' erase (Delete) or reset (End), nor left Shift+Alt
    assert not {k for _, k in used} & {DELETE, END}
    assert not [m for m, _ in used if m & (keys.LS | keys.LA) == keys.LS | keys.LA]


def test_functions_the_sim_may_have_nothing_for_take_shortcuts_whose_parts_do_nothing_in_flight():
    # an unbound shortcut can make MSFS fire a binding of its parts: for these, a menu key or the view
    shortcuts = every_shortcut()
    for name in keys.FIRST:
        mods, key = shortcuts[1, name]
        assert key in (INSERT, HOME, PAGE_UP, PAGE_DOWN, 0x4F, 0x50, 0x51, 0x52), name
        assert not mods & keys.LC or key in (0x4F, 0x50), name     # left Ctrl: autopilot references, not arrows


def test_the_report_puts_the_modifiers_around_the_key():
    # one step per pass: the modifiers, the key, the key up, the modifiers up; a function that follows at once
    # changes the modifiers without a report in between
    class Panel:
        down = None

        def pressed(self):
            return self.down

    panel, report = Panel(), bytearray(keys.REPORT)
    keyboard = keys.Keyboard(panel)

    def run(down, passes):
        panel.down, out = down, []
        for _ in range(passes):
            keyboard.fill(report)
            out.append((report[0], report[2]))
        assert not report[1] and not any(report[3:])
        return out

    a, b = (1, BM.BUTTON[1]["TEST"]), (2, BM.BUTTON[2]["COM_KHZ_UP"])
    (ma, ka), (mb, kb) = keys.shortcut(*a), keys.shortcut(*b)
    assert ma and mb and ma != mb
    assert run(None, 2) == [(0, 0), (0, 0)]
    assert run(a, 3) == [(ma, 0), (ma, ka), (ma, ka)]
    assert run(b, 4) == [(ma, 0), (mb, 0), (mb, kb), (mb, kb)]
    assert run(None, 3) == [(mb, 0), (0, 0), (0, 0)]


def test_shortcut_names():
    assert shortcut_name(keys.RC | keys.LA, INSERT) == "Right Ctrl+Alt+Insert"
    assert shortcut_name(keys.LC | keys.LS | keys.RS, F1 + 11) == "Ctrl+Shift+Right Shift+F12"


def test_solo_is_what_the_report_needs():
    # the report holds one key: a solo panel never has two buttons down (test_panel.py checks the timing)
    p = P.Panel(solo=True)
    p.key("AP", True, 0)
    p.turn("ALTHDG_OUTER", 1, 0)
    for t in range(1, 2000):
        p.tick(t)
        assert len(p.buttons(1)) + len(p.buttons(2)) <= 1
        if t == 500:
            p.key("AP", False, t)


# The shortcuts as of the first build with the keyboard mode: bindings in the sim depend on them. To change one on
# purpose, everyone's bindings have to change too; a new button takes a shortcut that no one has yet.
FROZEN = {
    1: (
        "Right Ctrl+F1", "Right Ctrl+F2", "Right Ctrl+F3", "Right Ctrl+F5", "Right Ctrl+F6", "Right Ctrl+F7",
        "Right Ctrl+F8", "Right Ctrl+F9", "Right Ctrl+F10", "Right Ctrl+F11", "Right Ctrl+F12", "Right Shift+F1",
        "Right Shift+F2", "Right Shift+F3", "Right Shift+F4", "Right Shift+F5", "Alt+Down", "Right Ctrl+Left",
        "Right Ctrl+Down", "Right Ctrl+Up", "Right Shift+F6", "Right Ctrl+F6", "Alt+Right", "Right Ctrl+F8",
        "Right Ctrl+F9", "Right Shift+F7", "Right Ctrl+F11", "Right Ctrl+F12", "Alt+Left", "Right Shift+F8",
        "Right Shift+F9", "Right Shift+F11", "Right Shift+F12", "Right Ctrl+Right Shift+F1",
        "Right Ctrl+Right Shift+F2", "Right Ctrl+Right Shift+F3", "Right Ctrl+Right Shift+F4",
        "Right Ctrl+Right Shift+F5", "Right Ctrl+Right Shift+F6", "Right Ctrl+Right Shift+F7",
        "Right Ctrl+Right Shift+F8", "Right Ctrl+Right Shift+F9", "Right Ctrl+Alt+Page Up",
        "Right Ctrl+Right Shift+F10", "Right Ctrl+Right Shift+F11", "Right Ctrl+Right Shift+F12", "Right Shift+Alt+F1",
        "Right Shift+Alt+F2", "Right Shift+Alt+F3", "Right Shift+Alt+F5", "Right Shift+Alt+F6", "Right Shift+Alt+F7",
        "Right Ctrl+Home", "Right Ctrl+Page Up", "Right Ctrl+Page Down", "Alt+Insert", "Alt+Home", "Right Shift+Alt+F6",
        "Right Shift+Alt+F7", "Right Ctrl+Home", "Right Ctrl+Page Up", "Right Ctrl+Page Down", "Alt+Insert", "Alt+Home",
        "Right Shift+Alt+F8", "Right Shift+Alt+F9", "Right Shift+Alt+F11", "Right Shift+Alt+F12",
        "Right Ctrl+Right Shift+Alt+F1", "Right Ctrl+Right Shift+Alt+F2", "Right Ctrl+Right Shift+Alt+F3",
        "Right Ctrl+Right Shift+Alt+F4", "Right Ctrl+Alt+Page Down", "Right Ctrl+Right Shift+Alt+F5",
        "Right Ctrl+Right Shift+Alt+F6", "Right Ctrl+Right Shift+Alt+F7", "Alt+Up", "Right Ctrl+Right Shift+Alt+F8",
        "Right Ctrl+Right Shift+Alt+F9", "Right Ctrl+Right Shift+Alt+F10", "Right Ctrl+Right Shift+Alt+F11",
        "Right Ctrl+Right Shift+Alt+F12", "Alt+F5", "Ctrl+Right", "Right Ctrl+Right", "Alt+F6", "Right Ctrl+Shift+F1",
        "Right Ctrl+Shift+F2", "Right Ctrl+Shift+F3", "Right Ctrl+Shift+F4", "Ctrl+Left", "Alt+F5",
        "Right Ctrl+Shift+F5", "Right Ctrl+Shift+F6", "Right Ctrl+Shift+F7", "Right Ctrl+Shift+F8",
        "Right Ctrl+Shift+F9", "Right Ctrl+Shift+F10", "Right Ctrl+Shift+F11", "Right Ctrl+Shift+F12",
        "Ctrl+Right Shift+F1", "Ctrl+Right Shift+F2", "Ctrl+Right Shift+F3", "Ctrl+Right Shift+F4",
        "Ctrl+Right Shift+F5", "Ctrl+Right Shift+F6", "Ctrl+Right Shift+F7", "Ctrl+Right Shift+F8",
        "Ctrl+Right Shift+F9", "Ctrl+Right Shift+F10", "Ctrl+Right Shift+F11", "Right Ctrl+Insert", "Alt+Page Up",
        "Alt+Page Down", "Right Ctrl+Alt+Insert", "Right Ctrl+Alt+Home", "Ctrl+Right Shift+F12",
    ),
    2: (
        "Right Ctrl+Right Shift+Alt+F5", "Ctrl+Right Shift+Alt+F9", "Ctrl+Right Shift+Alt+F10", "Alt+Up",
        "Right Ctrl+Right Shift+Alt+F8", "Right Ctrl+Right Shift+Alt+F9", "Right Ctrl+Right Shift+Alt+F10",
        "Right Ctrl+Right Shift+Alt+F11", "Right Ctrl+Right Shift+Alt+F12", "Alt+F5", "Ctrl+Right", "Right Ctrl+Right",
        "Alt+F6", "Right Ctrl+Shift+F1", "Right Ctrl+Shift+F2", "Right Ctrl+Shift+F3", "Right Ctrl+Shift+F4",
        "Ctrl+Left", "Alt+F5", "Right Ctrl+Shift+F5", "Right Ctrl+Shift+F6", "Right Ctrl+Shift+F7",
        "Right Ctrl+Shift+F8", "Right Ctrl+Shift+F9", "Ctrl+Right Shift+Alt+F11", "Ctrl+Right Shift+Alt+F12",
        "Ctrl+Shift+F5", "Ctrl+Shift+F6", "Ctrl+Shift+F7", "Ctrl+Shift+F8", "Ctrl+Shift+F9", "Ctrl+Shift+F10",
        "Ctrl+Right Shift+F6", "Ctrl+Right Shift+F7", "Ctrl+Right Shift+F8", "Ctrl+Right Shift+F9",
        "Ctrl+Right Shift+F10", "Ctrl+Right Shift+F11", "Right Ctrl+Insert",
    ),
}


def test_shortcuts_are_frozen():
    for dev, names in FROZEN.items():
        shortcuts = tuple(shortcut_name(*keys.shortcut(dev, b)) for b in range(len(names)))
        assert shortcuts == names, f"device {dev}: a shortcut moved"

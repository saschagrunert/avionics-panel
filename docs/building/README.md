# Building one

The steps from ordering to mapping.

```mermaid
flowchart LR
  jlcpcb["JLCPCB<br>2 assembled boards"]
  jlccnc["JLCCNC<br>front plate"]
  jlc3dp["JLC3DP<br>body, caps, knobs, light pipes"]
  jlcmc["JLCMC<br>screws"]
  local["Local shop<br>feet, cable, sandpaper, tools"]
  arrival["On arrival<br>checks"]
  bringup["Bring-up<br>flash and test"]
  assembly["Assembly"]
  mapping["Mapping<br>MobiFlight"]
  jlcpcb & jlccnc & jlc3dp & jlcmc & local --> arrival --> bringup --> assembly --> mapping
```

1. [Ordering](ordering.md): what to order where, step by step, with the
   [shopping list](ordering.md#shopping-list).
2. [Bring-up](bring-up.md): the checks on arrival and the cap set, then flashing the firmware and testing
   every key, knob and light on the bare board.
3. [Assembly](assembly.md): caps, light pipes, board, body and five screws, feet, knobs.
4. [Mapping](../using/mapping.md): the two joysticks in MobiFlight, or the
   [keyboard mode](../using/keyboard.md) for a console and for the sim without MobiFlight.

Two options: [Hand-soldering](hand-soldering.md) the keys, the encoders and the RANGE control, and the
[Pico bench](bring-up.md#pico-bench), which runs the firmware before the boards arrive.

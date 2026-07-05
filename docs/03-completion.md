---
status: complete
created: 2026-07-05
---
# L'Empereur — completion: the whole engine, walked

> The capstone. Every code bank is named and the native residue is resolved. This chapter ties
> [00-recon](00-recon.md) (engine placement), [01-data-tables](01-data-tables.md) (schema/strings),
> and [02-bank-map](02-bank-map.md) (load model + roles) into one picture: what the game *is* as
> software, the findings that fell out of the walk, and the method that got there.

## Status — done

| layer | result |
|---|---|
| **Fixed engine banks 30/31** | native floor + bytecode-OS **complete, 0 unnamed** (~318 native + 89 bytecode-OS; engine IS NA2's) |
| **18 code banks (0–12, 14–17)** | **all named** — **799 bytecode subroutines** ($E509) + **55 native helpers** = **854 labels** |
| **Bank 13** | recovered (was wrongly excluded) — 42 bytecode command subs |
| **Native residue** | resolved — **9 pure-native leaves** + **46 `$E2E3` trampolined natives** |
| **Record schema** | pinned command-first, re-confirmed 4 independent ways (see below) |
| **Symbol table** | `mesen-labels.toml`, ~**1300 labels** total |

0 decompile errors across every bank. The bytecode VM transferred wholesale from NA2/BK/NA1 — a new
title was retarget *addresses* in `koei-nes/tools/games.toml [lemp]`, not a code fork.

## The game as software — subsystem map

L'Empereur is an **OS-driven turn loop** (`os_main $E17D`, itself bytecode) over the KOEI Famicom VM,
with logic split across 8K paged banks. Grouped by role (per-bank detail in [02](02-bank-map.md)):

| subsystem | banks | what it is |
|---|---|---|
| **Universal library** | 0 | `$A000` display + game-state (faces/icons/map/HUD, record-list ops, the `$6EF6` country-relation matrix) |
| **Turn / command library** | 1 | `$8000` co-resident library serving the command cluster (banks 2–9) |
| **Turn-advance engine** | 17 | monthly upkeep + random events: tax/food/materials, starvation, population, officer aging/death/succession, decay, disasters |
| **Player commands** | 3, 4, 5, 6, 7 | economy/logistics · army/develop/personnel/national · **diplomacy** · **info/status views** · strategic war |
| **Computer-player AI** | 8, 9 | **domestic AI** (decide→execute per city/officer) · **diplomacy AI + turn brain** (relation-driven) |
| **Combat resolution** | 2 | combat AI + battle resolution + conquest (shared library) |
| **Tactical (field) battle** | 10, 11, 12, 13, 14 | `$8000` unit library · turn engine · setup/maneuvers · **player unit-orders + aftermath** · **battle AI** |
| **New-game / cinematics** | 15, 16 | scenario setup / endgame · opening / ending cinematics |

The two AI banks (8 domestic, 9 diplomacy) and the two tactical AI/player pairs (11 human ↔ 14 AI,
13 human orders) mirror each other — the same "decide vs execute" and "human ↔ AI" symmetry seen
across the KOEI conquest line.

## Record schema (command-first, quadruple-confirmed)

Offsets were pinned **only** when a command handler was caught writing one under a manual-confirmed cap
(e.g. `$270F`=9999, `$03E7`=999), never inferred. The **city record** (28 bytes, base `$7176`):

| off | field | off | field | off | field |
|---|---|---|---|---|---|
| +5 | population (word) | +16 | food | +24 | guns (cap 999) |
| +14 | gold | +18 | materials | +26 | wall / defense % |
| +8/+10/+11 | develop stats | +20 | soldiers | +27 | policy / event flags |
| | | +22 | horses (cap 999) | +2/+6 | governor / ruler ptr |

Confirmed **four independent ways** — the payoff of walking the whole engine rather than one bank:
1. **command handlers** (banks 3/4) write the caps; 2. **the AI** (banks 8/9) reads/writes the same
offsets from the other side; 3. **the info renderers** (banks 5/6) read them for display; 4. **the turn
engine** (bank 17, `move_army_to_city`) writes +20/+22/+24 from an officer. Four subsystems, one layout →
drift has nowhere to hide. Country reserves (`$7068`, 18 B): +8 gold / +10 food / +12 materials; the
symmetric country-relation matrix `$6EF6` (level&15 / at-war&16 / allied&32) and AI weights `$6FD7`.

## Findings — the intellectual payoff

**1. Engine ≠ configuration.** The cartridge *format* is pure NA2/BK (MMC5, 128K CHR, byte-identical
header, `RESET=$F500`), and the fixed engine bank matched NA2 to 0 unnamed — the machine *is* NA2's.
But the **syscall subsystem diverged**: the private vector relocated to `$FFDE` (GemFire-aligned), not
NA2/BK's `$FFF8` (which reads `$0000` here). Family by chassis, generation by firmware.

**2. Co-resident `$8000` libraries — a 5th call method.** Beyond trampolined cross-bank calls, an
`$A000`-resident app bank calls its co-resident `$8000` **library partner directly by address**. Two
libraries: **bank 1** serves the command cluster (2–9), **bank 10** serves the tactical banks (11/12/13/14).
The disassembler mis-tags these paged-window targets `{native}`; the fix was `coresident_N` config so the
partner's labels resolve. (First pass mis-scoped residence by "any `$8000` self-call"; corrected by a
*majority self-call window* test — the user's "don't rely on one call method" caught it.)

**3. The `$E2E3` native-call trampoline (the headline).** The engine has a *second* entry stub `$E2E3`
beside the `$E509` vm-entry. It is **not** a second bytecode class: its prologue builds a VM-style frame
(`$04`=fp over the caller's args, saves the VM regs) then `jmp ($0008)` into **native 6502 at stub+6**,
pushing `$E35A` so the body `RTS`es back into the VM. So the VM can `CALL_abs` a **native helper** as if
it were bytecode; the body reads args via `($04),y`. This is why 46 such subs (banks 0/1/2/8/9/10/12/14)
were correctly `{native}` yet callable from bytecode — e.g. bank 10's `cell_distance` (the battlefield
range primitive) and bank 0's `get_aggregate_stat`. Reversing the `$E2E3` prologue to its terminal
`jmp ($0008)` was what turned "a mysterious dialect" into "a native ABI." (Mid-walk we briefly mistook
it for a bytecode dialect; the terminal-jump trace corrected it — see the git history / [02](02-bank-map.md).)

**4. Bank 13 was hiding in plain sight.** It was excluded as an "anomaly" because its bank-entry *header*
is a `$E2E3` native trampoline — but its 42 command subs are standard `$E509` bytecode. Teaching the
census that the header ≠ the subs recovered a whole app bank: the **player battle-order handlers +
post-battle aftermath**.

## Method — how the walk was driven

- **Classify before choosing the method** — turn-based conquest sim ⇒ a walkable call tree, walked
  **leaves-first**: L0 = fixed floor (30/31), L1 = the universal library (bank 0), L2 = the two `$8000`
  co-resident libraries, then the app banks by ascending sub-count within each dependency layer.
- **Reuse/convert > rebuild** — every sub came from decompiling the ROM's own bytecode via the shared
  `koei-nes` VM (0 errors), never a re-implementation; every native helper from a seed-disasm of the ROM.
- **Grounding discipline** — offsets pinned only on a caught write; ambiguous disaster/event handlers
  named by *mechanism + the exact flag* they touch (not an invented disaster name); native leaf accessors
  named from call-site contracts + disasm, hedged where the semantics weren't provable.
- **Verification independence = dropping a layer** — the record schema is cross-checked against four
  subsystems (§ schema); the `$E2E3` finding against the 6502 itself (the terminal jump), not a second opinion.

## Open items

- **Dynamic bank args** — bank 1 `set_prg`×4, bank 31 `far_call`/`copy`/`set_prg`: bank computed at
  runtime → needs caller-value analysis to close those edges.
- **Data banks** 18, 21, 22, 24, 25 not yet dumped (19/20/26 done in [01](01-data-tables.md)).
- **Obscure native leaf accessors** carry hedged mechanism-names; a deeper native pass could sharpen them.
- **`$E2E3` ABI generality** — the native-trampoline convention should be checked against the next KOEI
  title that uses it (a candidate `koei-nes` toolchain feature rather than a per-game note).

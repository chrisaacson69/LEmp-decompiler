---
status: active
created: 2026-07-02
---
# L'Empereur — bank map & cross-bank dependencies

> How the 32 8K PRG banks load and call each other. Derived by scanning **every** cross-bank method
> across all decompiled banks (not just one) + own-call-window residence analysis. Bank value in any
> banking call masks **& 0x1F** → physical bank.

## Load model (MMC5 windows)

| window | addr | role |
|---|---|---|
| `$8000` | 8K | co-resident **engine/library** slot — one of the $8000-resident banks mapped here |
| `$A000` | 8K | the **current app bank** slot — app/logic banks rotate through here; bank 0 (library) swapped in via trampoline |
| `$C000` | 8K | bank 30 — semi-fixed OS-bytecode/UI-library + native helpers |
| `$E000` | 8K | bank 31 — fixed native VM engine + `os_main` |

## Residence (own-call-window analysis: majority self-call window)

- **`$8000`-resident:** banks **1, 10, 15, 16, 17** (all self-calls land in `$8xxx`).
- **`$A000`-resident:** banks **0, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14**.
- Banks **6, 9, 11** have a *small* dual-mapped `$8000` minority but are majority-`$A000` (decompiled there).
- Encoded as `banks_at_8000 = [1,10,15,16,17]` in `koei-nes/games.toml [lemp]`.

## Cross-bank methods (all of them — scanning one would miss banks)

| method | kind | count | bank operand |
|---|---|---|---|
| `call_in_bank_dcd1(win, bank, addr, …)` | code call | 784 | arg 2 |
| `copy_from_bank(mode, bank, src, …)` | data read | 124 | arg 2 |
| `block_copy_far` | data | 98 | (far ptr) |
| `copy_from_bank_dc80` | data | 58 | — (fixed src) |
| `memcpy_ptr` | data | 32 | — |
| `syscall_set_prg_bank(win, bank)` | map | 32 | arg 2 |
| `far_call(routine, bank)` / `call_module_*` | code (OS) | 28 | arg 2 |

**No dedicated far-call VM opcode** — cross-bank goes through trampolines OR direct co-resident calls.
**`far_call`/`set_prg` are the ONLY way bank 31's deps appear** — a `call_in_bank_dcd1`-only scan would
miss bank 31 (and the far-call-loaded banks 18, 22) entirely.

⚠ **A 5th method: direct co-resident `CALL_abs` into the `$8000` window** (NOT trampolined). An
`$A000`-resident bank calls its co-resident `$8000` **library** partner directly by address. The
disassembler mis-tags these paged-window targets as `{native}` (it can't see the real co-resident
bank), which is why the first pass missed them (the self-match residence test also masked them). **Two
shared `$8000` libraries:**
- **bank 1** ← called directly by banks **2, 3, 4, 5, 6, 7, 8, 9** (the main app cluster)
- **bank 10** ← called directly by banks **11, 12, 14**

So `coresident_N` IS needed (corrects an earlier note): `coresident_2..9 = [1]`, `coresident_11/12/14 = [10]`.

## Dependency graph (source → target(method))

| bank | role (all named) | depends on |
|---|---|---|
| 0 | **universal $A000 library — display + game-state** (faces/icons/map/HUD, record-list ops, the `$6EF6` country diplomacy matrix) | data: 19, 20, 26 |
| 1 | **$8000 turn/command/screen dispatcher library** (partner of 2-9) | calls 0; maps 1/5/24/25 (+ dynamic) |
| 2 | **combat AI + battle resolution + conquest** (shared library) | calls 0 |
| 3 | **economy / logistics commands** | call 0, 2 |
| 4 | **ARMY / develop / personnel / national commands** | call 0, 2 |
| 5 | **diplomacy commands + country/city info cards** | calls 0, 2, 4; data 26 |
| 6 | **INFO / status-view subsystem + system menu** | calls 0, 2, 4, 5; data 20 |
| 7 | **strategic (map-level) war orchestration** | calls 0, 2; data 26 |
| 8 | **computer-player domestic AI** (decide → execute) | calls 0, 2 |
| 9 | **computer-player diplomacy AI + turn brain** | calls 0, 2, 5 |
| 10 | **$8000 tactical (field) battle library** (partner of 11/12/14) | calls 0; maps 1/5; data 19, 21, 26 |
| 11 | **tactical battle turn engine** (human + AI unit control) | calls 0; data 20 |
| 12 | **tactical battle setup + special combat maneuvers** | calls 0, 11; maps 1/5; data 5, 19, 21 |
| 14 | **tactical battle AI** (per-unit decision engine) | calls 0, 11, 12, 21 |
| 15 | **$8000 new-game setup / scenario / endgame** | calls 0; data 26 |
| 16 | **$8000 opening / ending cinematics** | data 19 |
| 17 | **$8000 turn-advance / monthly-upkeep + events engine** | calls 0; maps 1/5 |
| 30 | OS/UI bytecode lib | maps 1/5; data 19, 20, 26 |
| 31 | fixed OS (`os_main`) | far_call 2/11/18/20; maps 0/1/5/30 (+ dynamic) |

### Reverse (most-depended-on)
- **bank 0** ← 16 callers (everything) — the core library.
- **bank 2** ← 8 (3,4,5,6,7,8,9,31); **bank 5** ← 8 (1,6,9,10,12,17,30,31); **bank 1** ← 6.
- **data:** bank 26 (names/records) ← 6; bank 19 (font/scenes) ← 5; bank 20 (messages) ← 5; bank 21 ← 3.
- **banks 18, 22** are reached **only** via bank 31 `far_call` (invisible to a code-call-only scan).

## Leaves-first walk order (by code-call dependency; within a layer, fewest subs first) — **ALL DONE**

Every code bank (0-12, 14-17; bank 13 absent) is now named — **1207 labels total** across the TOML.

- **L0** = fixed floor, banks 30/31 — **DONE** (native floor + bytecode-OS, 0 unnamed).
- **L1** = **bank 0** (61 subs) — **DONE** ($A000 display + game-state library; all 16 callers resolve it).
- **L2 = the two `$8000` co-resident libraries** — **DONE**: **bank 1** (partner of banks 2-9) and
  **bank 10** (partner of 11/12/14). Precede their clusters despite their size.
- **L3-L5 = the app/logic banks** — **DONE**: command handlers 3/4/7/8, diplomacy 5, info 6, AI 8/9;
  tactical battle 10/11/12/14; setup/cinematics 15/16; the turn engine 17.
- Two AI banks (9, 14) also carry **native `{native}` helpers** in their own window (diplomacy/city
  target-pickers `$BAD3`/`$BCB0`; unit/cell scanners `$BAF7`/`$B9A0`) — named from their call contracts.

The record-field schema was pinned **command-first** (an offset is named only when a handler is caught
writing it under a manual-confirmed cap) and then **re-confirmed** independently by the AI banks (8/9),
the info renderers (5/6), and the turn engine (17). City: +5 pop, +14 gold, +16 food, +18 materials,
+20 soldiers, +22 horses, +24 guns, +26 wall, +27 policy/event flags.

## Open items
- **Dynamic bank args** (bank 1 `set_prg`×4, bank 31 `far_call`/`copy`/`set_prg`): the bank is computed
  at runtime → needs caller-value analysis to resolve those edges.
- **Data-bank contents:** 21, 22, 24, 25, 18 not yet dumped (19/20/26 done in [01-data-tables](01-data-tables.md)).
- **Native `$9000` helper residue** inside the `$8000` library banks (1, 10, 15, 16, 17) and the
  AI banks' `$B600+` native helpers (14) — a separate native-naming pass, not the bytecode walk.

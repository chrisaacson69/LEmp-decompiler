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

**No dedicated far-call VM opcode** — cross-bank always goes through these trampolines. **`far_call`/
`set_prg` are the ONLY way bank 31's deps appear** — a `call_in_bank_dcd1`-only scan would miss bank 31
(and the far-call-loaded banks 18, 22) entirely. **No direct co-resident `CALL_abs` exists** (own-call
analysis found 0 non-self cross-window calls) → **no `coresident_N` config needed** (unlike NA2).

## Dependency graph (source → target(method))

| bank | role | depends on |
|---|---|---|
| 0 | **universal $A000 library — display + game-state** (faces/icons/map/HUD, record-list ops, the `$6EF6` country diplomacy matrix) | data: 19, 20, 26 |
| 1 | $8000 dispatcher/library | calls 0; maps 1/5/24/25 (+ dynamic) |
| 2 | shared library | calls 0 |
| 3, 4 | app logic | call 0, 2 |
| 5 | app logic + shared | calls 0, 2, 4; data 26 |
| 6 | app logic | calls 0, 2, 4, 5; data 20 |
| 7 | app logic | calls 0, 2; data 26 |
| 8 | app logic | calls 0, 2 |
| 9 | app logic | calls 0, 2, 5 |
| 10 | $8000 engine | calls 0; maps 1/5; data 19, 21, 26 |
| 11 | app logic | calls 0; data 20 |
| 12 | app logic | calls 0, 11; maps 1/5; data 5, 19, 21 |
| 14 | **top-level orchestrator** | calls 0, 11, 12, 21 |
| 15 | $8000 engine | calls 0; data 26 |
| 16 | $8000 engine | data 19 |
| 17 | $8000 engine | calls 0; maps 1/5 |
| 30 | OS/UI bytecode lib | maps 1/5; data 19, 20, 26 |
| 31 | fixed OS (`os_main`) | far_call 2/11/18/20; maps 0/1/5/30 (+ dynamic) |

### Reverse (most-depended-on)
- **bank 0** ← 16 callers (everything) — the core library.
- **bank 2** ← 8 (3,4,5,6,7,8,9,31); **bank 5** ← 8 (1,6,9,10,12,17,30,31); **bank 1** ← 6.
- **data:** bank 26 (names/records) ← 6; bank 19 (font/scenes) ← 5; bank 20 (messages) ← 5; bank 21 ← 3.
- **banks 18, 22** are reached **only** via bank 31 `far_call` (invisible to a code-call-only scan).

## Leaves-first walk order (by code-call dependency; within a layer, fewest subs first)

- **L0** = fixed floor, banks 30/31 — **DONE** (native floor + bytecode-OS, 0 unnamed).
- **L1** = **bank 0** (61 subs) — **DONE** (display + game-state library; every one of the 16 callers now
  resolves bank-0 names). Its 42-caller reach makes it the highest-leverage bank.
- **L2** = banks that call only bank 0 — 15(18), 16(19), 2(26), 11(55), 17(60), 1(61), 10(61).
  *(Bank 2 is the 2nd-most-called after 0, so it unblocks the most L3 despite not being smallest.)*
- **L3** = 12(22), 8(32), 3(43), 4(49), 7(54) — add bank 2 or 11.
- **L4** = 5(34), 14(43). **L5** = 6(45), 9(74) — deepest orchestrators.

The record-field schema stays generic (`field_N`) until a command handler in these banks is caught
writing an offset with a manual-confirmed cap — that's how L2-L5 will pin gold/soldiers/loyalty.

## Open items
- **Dynamic bank args** (bank 1 `set_prg`×4, bank 31 `far_call`/`copy`/`set_prg`): the bank is computed
  at runtime → needs caller-value analysis to resolve those edges.
- **Data-bank contents:** 21, 22, 24, 25, 18 not yet dumped (19/20/26 done in [01-data-tables](01-data-tables.md)).
- The `banks_at_8000` residence is set; app-bank subs are still unnamed (the command-walk is next).

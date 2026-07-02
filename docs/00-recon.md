---
status: active
created: 2026-07-02
---
# First-contact recon — L'Empereur (vs NA2 / BK, the MMC5 128K-CHR family)

> L'Empereur is KOEI's **8th** NES strategy title and the **last of the NES conquest sims**, the
> first set outside East Asia (**Napoleonic Europe**, 1789–1815). This recon places it in the
> engine family, locates its VM/OS constants, and self-dates it against its closest siblings
> **NA2 (game 4)** and **BK (game 6)**. Every claim here is byte-grounded in the ROM
> (`Empereur, L' (USA).nes`, 393232 B); nothing below is inherited on faith.

## Cartridge profile — squarely in the NA2/BK sub-family

iNES header `4E 45 53 1A 10 10 52 08 …` decodes byte-identically to NA2 and BK:

| | mapper | PRG | CHR | file | header f6/f7 |
|---|---|---|---|---|---|
| NA2 (game 4) | 5 (MMC5) | 256K | 128K CHR-ROM | 393232 B | 52 / 08 |
| BK (game 6) | 5 (MMC5) | 256K | 128K CHR-ROM | 393232 B | 52 / 08 |
| RotK II / GemFire (5,7) | 5 (MMC5) | 256K | **256K** CHR-ROM | 524304 B | 52 / 08 |
| **L'Empereur (game 8)** | **5 (MMC5)** | **256K** | **128K CHR-ROM** | **393232 B** | **52 / 08** |

Size math closes: `16 + 262144 (PRG) + 131072 (CHR) = 393232`. So L'Empereur is in the **128K-CHR
sub-family (NA2/BK)**, *not* the 256K-CHR flavor (RotK II / GemFire). This settled the "which
flavor of MMC5" question at the format level before any code was read.

## Not a byte-twin — a genuine sibling RE

Unlike GemFire (a near-zero-change ROM-twin of RotK II), L'Empereur is its own game:

| measure | LEmp vs NA2 | LEmp vs BK |
|---|---|---|
| PRG bytes identical (fixed offsets) | ~3.5% | ~3.2% |
| fixed bank ($C000–$FFFF) identical | ~2.9% | ~2.6% |
| **RESET routine `$F500` first 64 B** | **49 / 64** | 25 / 64 |

The low whole-ROM match is expected (different game, code relocated). The signal that matters is the
**reset routine**: L'Empereur's **first 29 boot bytes are byte-identical to NA2** and it is far
closer to NA2 than to BK — so **NA2 is the base title**.

## CPU vectors — engine in the MMC5 fixed tail

Last 16 bytes of PRG (`$FFF0–$FFFF`): `00 00 4c f6 00 f5 47 ff` in the vector slots →

| vector | L'Empereur | NA2 | BK |
|---|---|---|---|
| NMI (`$FFFA`) | `$F64C` | `$F641` | `$F641` |
| RESET (`$FFFC`) | **`$F500`** | `$F500` | `$F500` |
| IRQ/BRK (`$FFFE`) | `$FF47` | `$FF34` | `$FFD6` |
| (`$FFF8`) | **`$0000`** | `$F8E7` | `$F8ED` |

`RESET=$F500` (shared across all three) is the KOEI-MMC5 engine tell: boot high in the fixed tail,
MMC5 pinning the last 8K at `$E000–$FFFF`. **`$FFF8`=`$0000` is the divergence** — NA2/BK route
syscalls through a *private* pseudo-vector there (`$F8E7`/`$F8ED`); L'Empereur does **not**. This was
recon target #1 — **now RESOLVED**: the private vector is *relocated to `$FFDE`* (see the native-floor
section below). The format groups L'Empereur with NA2/BK; this engine detail groups it with **GemFire**.

## Boot flow

`$F500` reset → standard PPU warmup (disable `$2000`/`$2001`, wait 2 vblanks via `$2002`, `×$0F`
clear loop, `txs`) → init-sub chain: `$F5BA`, **`$F53D`**, `$F559`, `$F597`, `$F5AF`, `$F5CF`,
`$F5E8`, `$F5FC`, `$F611`, `$F9CD` → `jmp $E000` → `$E000` = `JMP $E17D` → **OS main at `$E17D`**.
`$E17D` = `20 09 e5 …` = **`JSR $E509` (vm_entry) + inline operands** — the OS main is itself
bytecode, exactly as in NA2 (`$E10C`). Init sub **`$F53D`** occupies the same slot NA2 used for its
MMC5 banking programmer — the likely banking-setup routine here too (to confirm in ch. 01).

## Bytecode VM — same machine, `vm_entry = $E509` (the crown jewel transfers)

Every paged 8K bytecode bank opens with a `JMP <init> / JSR vm_entry` header; the `JSR` target is the
mode across banks:

- **`vm_entry = $E509`** (stub `20 09 e5`), present at +3 of banks **0–12, 14–17, 30, 31** (19 banks).
- **`$E509` fingerprint:** pulls the post-`JSR` return address off the stack into the inline
  operand/bytecode pointer, then `LDY #$07 / SEC / LDA $02 / SBC #$09 / STA $0C …` — the family
  **9-byte call frame**, `vm_sp=$02`.
- **Dispatcher `$E54D` = `vm_entry + 0x44`** — the family-invariant structural offset holds exactly:
  ```
  $E54D  ldy #$00
         lda ($06),y / inc $06 / bne + / inc $07   ; fetch opcode at vm_ip, advance (16-bit)
         tax
         lda $ED1E,x → $00                          ; handler_lo table
         lda $EE1E,x → $01                          ; handler_hi table (= lo + 0x100)
         jmp ($00)                                  ; dispatch; handlers jmp back to $E54D
  ```

| const | L'Empereur | NA2 | na1 |
|---|---|---|---|
| `vm_entry` | **`$E509`** | `$E414` | `$E823` |
| dispatcher (= entry+`0x44`) | **`$E54D`** | `$E458` | `$E867` |
| `handler_lo` / `handler_hi` | **`$ED1E` / `$EE1E`** | `$EC29`/`$ED29` | `$F026`/`$F126` |
| VM regs | `vm_sp=$02 vm_ip=$06`, 9-byte frame | same | same |

## Bank census (8K banks)

| banks | header | role |
|---|---|---|
| 0–12, 14–17 | `JMP <init> / JSR $E509` | **bytecode** (app logic) — 17 app banks |
| 13 | `JMP $A003 / JSR $E2E3` | **native** — `$E2E3`=`native_fn_prologue` (not a bytecode bank; see below) |
| 18–29 | no clean header (data/strings/tiles) | data / native |
| 30 | `JMP $C003 / JSR $E509` | semi-fixed lower bank (`$C000–$DFFF`) |
| 31 | `JMP $E17D / JSR $E509` | **true fixed bank** (`$E000–$FFFF`) — reset + vectors + VM engine |

**Toolchain wrinkle (inherited from NA2):** the shared `disasm6502.py`/`koei_vm.py` assume **16K**
banks; L'Empereur pages **8K** at `$8000`/`$A000` like NA2, so it uses the same 8K-bank mode
(`bank_size=0x2000` in the `[lemp]` profile). Default bytecode window is `$A000` (the `JMP $A003`
majority).

## Fixed-bank native floor — the engine IS NA2's, the syscall subsystem is GemFire-era

Full native-6502 recon of the fixed engine region `$C000–$FFFF` (banks 30+31) via
`tools/native_floor.py` (converted from GemFire's; **oracle = NA2**, signature-match auto-naming):

| | count | meaning |
|---|---|---|
| native subs enumerated | **307** | recursive-descent reach ∪ JSR-census ∪ vector/handler/syscall seeds |
| relocated-identical to NA2 (≥.90) | 229 | shared engine floor — inherit NA2's canonical name verbatim |
| hand-read residue (<.90) | 71 | renumbered syscall handlers + MMC5 primitives + reworked ALU — read + named |
| phantoms flagged | 9 | JSR-census artifacts (data/bytecode false targets, mid-instruction off-by-ones) — **not subs** |

**Floor COMPLETE — 0 unnamed** (`mesen-labels.toml`, 309 labels: **300 real native subs named** + 9
phantoms flagged), matching the standard of every prior game. **The engine *is* NA2's** (VM core,
16-bit division ALU, `vm_load_ptr*`/`vm_store_*` helpers, NMI PPU pipeline, kernel helpers all
relocated-identical). `vm_entry $E509` scores **1.00 vs NA2 `$E414`** (89 callers); `vm_dispatch
$E54D` 1.00; `nmi_handler $F64C` 0.91.

The hand-read residue confirmed the engine identity down to the details: the **32-bit ALU** (`add32
$D779`, chained `shl32 $D78E/$D799/$D7A4`, `mul_wide $D69D`, and a **`mul32_mmc5 $EFCB`** that
multiplies via the **MMC5 hardware multiplier `$5205/$5206`**), the **NMI PPU-flush pipeline**
(`$F719–$F8D7`), the **boot init chain** (`$F53D` clears RAM — *not* banking, correcting a first-pass
guess), and the **ext-op sub-dispatcher `$EF50`** (table `$EF6B`) for the 32-bit-math extended opcodes.

### Syscall subsystem (recon #1 — RESOLVED): private vector RELOCATED to `$FFDE`

This is the **engine-vs-config divergence**. The cartridge format is NA2/BK-family, but the syscall
path matches **GemFire (game 7)**, not its format-siblings:

- Bytecode invokes a syscall via `CALL_abs $EF1E, <id>` (seen in every bytecode bank, e.g.
  `CALL_abs_imm1 $EF1E (syscall_entry_struct) {native}, $10`).
- **`$EF1E`** = NA2's `$EE29` analog: copy a 22-byte param struct `($02)→$004E+`, push a fake-BRK
  frame, `jmp ($FFDE)`, then `$66/$67→$08/$09` return (the family convention). `$EF3E` = the
  lightweight variant (id in `A`), NA2's `$EE49` analog.
- **`$FFDE`** is the private syscall pseudo-vector = **`$F961`** (NA2/BK use `$FFF8`; L'Empereur's
  `$FFF8`=`$0000`). **GemFire also uses `$FFDE`** → L'Empereur is GemFire-era on this axis.
- **`$F961`** dispatcher: save A/X/Y, clear `$66/$67`, push central return `$F984`, `lda $50` (id) /
  `asl` / index **table `$F98B`** / `jmp ($006F)`. `$F984` = `pla×3 / rti` (consumes the fake-BRK frame).
- **Table `$F98B`** — raw 2-byte addresses, **27 slots** (NA2 had 31, GemFire 28), id0=`$F500` reset,
  handlers `$FA8F–$FF3A`. Renumbered vs NA2 (MMC5 bank/CHR/ExRAM primitives).

| Title | private syscall vector | dispatcher | table | slots |
|---|---|---|---|---|
| NA2 (game 4) | `$FFF8` | `$F8E7` | `$F911` | 31 |
| BK (game 6) | `$FFF8` | — | — | — |
| **GemFire (game 7)** | **`$FFDE`** | `$F91C` | `$F946` | 28 |
| **L'Empereur (game 8)** | **`$FFDE`** | **`$F961`** | **`$F98B`** | **27** |

**Takeaway (Chris's point, made concrete):** *format ≠ engine.* Classifying by cartridge shape put
L'Empereur with NA2/BK; the engine's syscall subsystem evolved with the later titles and sits with
GemFire. The full recon on the fixed bank was needed to see it — the config alone would mislead.

### Bank 13 anomaly — RESOLVED

Bank 13's `JSR $E2E3` (not `$E509`) targets **`$E2E3` = `native_fn_prologue`** (NA2 `$D8AB`, score
0.97) — so bank 13 is entered as **native** code, not bytecode. It is not a VM bytecode bank.

## Bottom-up fixed-bank bytecode — and how it CLOSES the native floor

The two fixed banks hold bytecode too (the OS/UI library), not just native code:
`koei_vm.py disasm lemp 30/31` finds **76 bytecode subs in bank 30** + **13 in bank 31** (incl.
`os_main $E17D`). Decompiled on the named floor, all 89 come out with **0 errors** and every engine
call resolved — `os_main` reads as clean C (`map_default_banks(); copy_from_bank_dc80(0x6000,…);
init_display(); … dispatch_screen_mode();`).

**Toolchain enhancement (baked in):** L'Empereur invokes syscalls as `CALL syscall_entry_struct(id,
…)`, so the decompiler rendered the raw id. `koei_vm.py` now resolves `<syscall_entry>(<literal id>,
…)` → the id's handler name via the syscall table (`resolve_syscall_entry_calls`); general, opt-in by
config, benefits app banks too.

**The floor was incomplete — bottom-up closed it.** The native-only floor seeds from
vectors/handlers/JSR-census, but **18 native subs are reached ONLY via bytecode `CALL_abs`** (no native
JSR), so they were missed — including `copy_from_bank $F3A3` (**14 bytecode callers**),
`call_in_bank_dcd1 $DD79`, `copy_from_bank_dc80 $F423`, `memcpy_ptr`, `block_copy_far`, `min_s16`/
`max_s16`. Seeding `native_floor.py` from the bytecode `{native}` CALL targets (`BYTECODE_LEAVES`)
enumerates + classifies them; 11/18 were relocated-identical to NA2. **Complete floor = native-reachable
∪ bytecode-reachable** — 325 subs, still 0 unnamed. This is the load-bearing lesson: the pure-native
floor is a lower bound; the bytecode layer reveals the rest of the floor beneath it.

**Bytecode OS layer — COMPLETE (both fixed banks, 89/89 subs named):**
- **Bank 31 (13):** `os_main`, `far_call`, `init_display`, `load_screen_data`, `dispatch_screen_mode`,
  `map_default_banks`, `call_module_*`.
- **Bank 30 (76):** the shared **UI/OS toolkit** — a full C runtime + application services:
  - *string/number:* `strcpy` `strcat` `atoi` `parse_uint` `utoa` `vsprintf` `format_value`
    `toupper` `tolower` `str_display_width`
  - *input:* `read_controller` `wait_key` `input_number` `yes_no_prompt` `grid_menu_select`
    `wait_button_repeat`
  - *render:* `draw_string` `draw_cursor` `draw_record_sprite` `upload_bg_tiles`/`free_bg_tiles`
    `switch_screen` `set_screen_mode` `flush_vram`
  - *audio:* `change_music` `play_sfx` `stop_music` `is_music_playing`
  - *records:* `record_name_7068/7176/6005`, `record_field_7176/6005`, `record_ptr_*` (base-address
    qualified — entity identity province/officer/unit still TBD, pending the record-schema walk)

Labels in `[prg.bank30]` (76) + `[prg.bank31]` (native floor + 13 bytecode). One item to verify: syscall
**id16 `$FCF4`** is used purely as a controller read (button-bit switch) — likely `read_controller`, not
the NA2-inherited `get_prg_bank` name (low-confidence match).

## Data-walk (before the app-bytecode walk) — names the data, which names the subs

The record accessors and `draw_string` sites reference concrete data addresses, so naming that data
first lets the subs name themselves (`dump_data.py`; KOEI UI text = NUL-terminated ASCII).

**Record schema — resolved from the name pools** (the standout result). `copy_from_bank` bank values
mask by `& 0x1F` → physical 8K bank; the three name tables live in **bank value 250 → physical bank 26**:

| record base | stride | **entity** | name table (bank 250) | sample names |
|---|---|---|---|---|
| `$6005` | 15 | **generals** | `$A65A` stride 17 | Napoleon, Berthier, Talleyrand, Barras |
| `$7068` | 18 | **countries** | `$A004` stride 10 | France, Holland, Bavaria, Prussia, Spain |
| `$7176` | 28 | **cities** | `$A09A` stride 32 | Dublin, London, Amsterdam, Stockholm |

This retired the "entity identity TBD" placeholder: the bank-30 accessors were renamed
`record_*_7068/7176/6005` → **`country_*` / `city_* `/ `general_*`** (`country_name`, `city_ptr`,
`general_field`, `draw_general_sprite`, …).

**Fixed-bank UI string pool** (`$DF16-$DF57`, ASCII) — named `str_yn_prompt "(Y/N)?"`, `str_yes`,
`str_no`, `str_ok`, `str_range_prompt "(%d-%d)?"`, and the debug templates `str_dbg_c0pc "C0PC = %d"`
/ `bk4=%d` / `bk5=%d` (which confirm `$C003 fatal_hang` is a developer crash screen). `yes_no_prompt`
now reads `draw_string(str_yn_prompt)` etc.

**Message bank located:** bank value 244 → physical bank 20 holds the diplomacy/economy text
(`"Distribute how much"`, `"Country's %s"`, `"reflect on your honor as a nation"`) — registered as
`[prg.bank20]`; bank 243 → physical 19 = font/charmap + scene headers (`load_scene`). Full
message-table naming is the next data-walk tranche.

**Lesson:** data-walk *before* the app-bytecode walk. Identifying generals/countries/cities up front
means the app banks (0-12,14-17) will decompile with real entity + field names from the start.

## Reuse vs new — scorecard

| | Reused (engine family holds) | New (this title) |
|---|---|---|
| Cartridge | ✓ MMC5 / 256K PRG / 128K CHR — NA2/BK shape | Napoleonic-era content |
| Bytecode VM | ✓ **same machine** — `$00–$07` frame, `vm_sp/ip=$02/$06`, dispatcher = entry+`0x44`, `jmp($00)` | retargeted addrs (`vm_entry=$E509`, `handler_lo=$ED1E`) |
| Boot/init | ✓ warmup → init-sub chain → `jmp $E000` → OS bytecode | init subs relocated; `$F53D` = likely banking |
| Fixed engine | ✓ last-16K-as-engine (banks 30+31), fixed region `$E000–$FFFF` | |
| Bytecode banking | ✓ 8K bytecode banks with `JSR vm_entry` header | bank 13 anomaly (`JSR $E2E3`) |
| BIOS syscalls | ✓ fake-BRK convention + 22-byte param struct (`$EF1E`) + `$66/67→$08/09` return — inherited from NA1/NA2 | private vector **relocated to `$FFDE`** (`$F961` dispatch, `$F98B` table, **27** slots) — matches **GemFire**, not format-siblings NA2/BK (`$FFF8`) |

## Open items (next steps)

1. **Syscall dispatch (recon #1)** — **RESOLVED**: private vector relocated to `$FFDE`→`$F961`,
   27-slot table `$F98B`, entries `$EF1E`/`$EF3E`; bytecode calls via `CALL_abs $EF1E, <id>`. Matches
   GemFire's `$FFDE` placement, not NA2/BK's `$FFF8`. Constants in `[lemp]`; floor in `mesen-labels.toml`.
2. **Register `[lemp]`** in `koei-nes/tools/games.toml` — **DONE** (this session), seeded from `[na2]`;
   `mesen-labels.toml` stub created with the verified fixed-bank floor.
3. **VM 8K-bank bring-up** — **DONE**: `koei_vm.py disasm lemp 0` tiles cleanly into **61 bytecode
   subs** with the family opcode set (no garbage), confirming `vm_entry=$E509` / dispatcher `$E54D` /
   `handler_lo/hi=$ED1E/$EE1E`. The VM transfers with zero code changes. Mass runs unblocked.
4. **Opcode census** — count implemented handlers in `$ED1E`/`$EE1E`; predict it matches the family
   ~219 (VM transfers with only the retargeted constants).
5. **Bank 13 anomaly** — **RESOLVED**: `$E2E3` = `native_fn_prologue` (NA2 `$D8AB`); bank 13 is
   entered as native code, not a bytecode bank.
6. **Boot init-sub identification** — confirm `$F53D` = MMC5 banking programmer (NA2 parallel).
7. **Native-floor residue** — **DONE**: all 71 hand-read + named (syscall handlers `$FA8F–$FF3A`,
   ALU, NMI pipeline, boot chain); 9 census-phantoms flagged. Floor at 0-unnamed. *Possible tool
   follow-up:* tighten `native_floor.py`'s `is_code` filter so those 9 phantoms aren't emitted.
8. **Full `source/` ladder** — mass disasm/decompile bytecode banks 0–12, 14–17 now tiling is confirmed.
   (Native floor is done; this is the bytecode/game-logic phase — the next major step.)

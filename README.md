# LEmp-decompiler — L'Empereur (NES, USA, 1991)

> KOEI's **8th** NES strategy title and the **last of the NES conquest sims**, set outside the
> Sino-Japanese world for the first time: **Napoleonic Europe**. Structurally it is a **sibling of
> Nobunaga's Ambition II** — same MMC5 / 256K-PRG / **128K CHR-ROM** cartridge (393232 B, header
> byte-identical to NA2/BK), same KOEI bytecode VM engine, `RESET=$F500`. This is **not** a
> zero-change ROM-twin like GemFire↔RotK II; the game content is its own (~3% raw byte match) and
> the syscall convention differs. Thin game repo over the shared `koei-nes` engine library (sibling clone).

## Status

First-contact recon + **full fixed-bank native-floor walk** done (2026-07-02). The **bytecode VM
transfers** — same machine as na2/bk/na1, only the addresses moved. Fixed engine bank walked vs NA2 to
**0 unnamed** (300 native subs named, 229 relocated-identical + 71 hand-read), so the engine *is* NA2's. The one real divergence —
the **syscall subsystem** — is resolved: private vector relocated to `$FFDE` (GemFire-aligned), not
NA2/BK's `$FFF8`. **Engine ≠ config**: format says NA2/BK-family, syscall says GemFire-era.

| const | value | note |
|---|---|---|
| mapper / CHR | MMC5 / 128K CHR-ROM | NA2/BK family (not RotK II/GemFire's 256K-CHR flavor) |
| ROM / header | 393232 B / iNES `4E45531A 10105208 …` | byte-identical header to NA2 and BK |
| RESET / OS entry | `$F500` / `$E17D` | OS main is itself bytecode (`$E17D` = `JSR $E509` + inline operands) |
| NMI / IRQ | `$F64C` / `$FF47` | NMI ~11 B off NA2's `$F641`; timing off NMI |
| `vm_entry` / dispatcher | `$E509` / `$E54D` (= entry+`0x44`) | **family-invariant offset holds** |
| `handler_lo` / `handler_hi` | `$ED1E` / `$EE1E` | `hi = lo + 0x100` |
| VM registers | `vm_sp=$02`, `vm_ip=$06`, 9-byte call frame | identical to na1/na2/bk |
| bytecode banks | **8K** windows 0–12, 14–17 (+ fixed 30/31); bank 13 = native | 8K banks like NA2 → toolchain 8K mode |
| syscall | private vector **`$FFDE`**→`$F961`, table `$F98B` (27 slots) | ⚠ NOT NA2/BK's `$FFF8` — matches **GemFire**; entry `$EF1E`/`$EF3E` |
| native floor | **COMPLETE, 0 unnamed** — 318 subs named (incl. 18 bytecode-reachable leaves) + 9 phantoms | engine IS NA2's; syscall subsystem diverged |
| fixed-bank bytecode-OS | **COMPLETE, 0 unnamed** — 89 subs (bank 31 OS/loop + bank 30 UI toolkit) | bottom-up on the named floor; 0 decompile errors |

## Base title

Closest sibling by reset-routine match: **NA2 (49/64 bytes)** ≫ BK (25/64). The `[lemp]` profile in
`koei-nes/tools/games.toml` is seeded from `[na2]` and retargeted to the constants above.

## Entry point

Engine constants live in the `[lemp]` block of `koei-nes/tools/games.toml`; the symbol table will be
`mesen-labels.toml` (not yet generated). Start with [docs/00-recon.md](docs/00-recon.md).

## Chapters (planned — the standard set)
- [00 — Recon](docs/00-recon.md): first-contact, MMC5 family placement, engine constants, native floor, bottom-up bytecode, data-walk. **← done**
- [01 — Data tables & strings](docs/01-data-tables.md): data-bank map, record schema (generals/countries/cities), name tables, UI strings, message pool. **← done**
- [02 — Bank map & cross-bank deps](docs/02-bank-map.md): load model, residence ($8000 vs $A000), all cross-bank methods, dependency graph. **← done**
- 01 — Boot & dispatch: reset → OS (`$E17D`) → VM → the OS-driven turn model.
- 02 — Control flow: the bytecode VM, MMC5 cross-bank call forms, native ABI.
- 03 — Player commands & record schema.
- 04 — AI architecture.
- 05 — Events & lifecycle (the Napoleonic calendar / diplomacy layer).
- 06 — Combat overview.
- 07 — Tactical engine.

Cross-game record schemas: `koei-nes/tools/RECORD_SCHEMAS.md`. The ROM is **not committed**
(copyright); it lives at `LEmp-decompiler/<rom>` per the resolver. Game manual in `docs/` (also
gitignored).

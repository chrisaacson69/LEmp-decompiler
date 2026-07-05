#!/usr/bin/env python3
"""
native_floor.py - L'EMPEREUR fixed-bank NATIVE-6502 floor: enumeration + canonical naming vs NA2.

L'Empereur retarget of GemFire-decompiler/tools/native_floor.py (reuse > rebuild). The fixed engine
bank is the last 16K ($C000-$FFFF = MMC5 banks 30+31); it holds firmware -> kernel helpers -> the
bytecode VM -> the ALU. L'Empereur is in NA2/BK's MMC5 128K-CHR sub-family and its RESET routine is
byte-closest to NA2 (49/64), so **NA2 is the oracle** (fully named; it in turn absorbed NA1's
canonical engine names). Shared subs inherit NA2's name by relocation-invariant signature match; the
residue (<.70) is a placeholder for a human read.

*** ENGINE-vs-CONFIG DIVERGENCE (the point of this walk) ***
  The cartridge FORMAT says NA2/BK-family, but the ENGINE need not match. First proof: NA2/BK route
  syscalls through a PRIVATE pseudo-vector at $FFF8 ($F8E7 / $F8ED). L'Empereur has **$FFF8 = $0000** --
  that mechanism is absent/relocated. So this floor does NOT hardcode a syscall vector; it enumerates
  natives via vectors + VM opcode-handler tables + JSR-census + recursive-descent reach, and the
  syscall dispatch is expected to surface as a residue sub reachable from a VM opcode handler. Once
  found, add it as a seed and re-run (mirrors how NA2/GemFire seeded their syscall path).

L'Empereur specifics (all in koei-nes/games.toml [lemp]; see docs/00-recon.md):
  - vm_entry stub = `20 09 e5` (JSR $E509);  dispatcher $E54D (= entry+0x44);  handler tables $ED1E/$EE1E
  - OS main $E17D (itself bytecode);  RESET $F500;  NMI $F64C;  IRQ/BRK $FF47
  - the fixed bank INTERLEAVES bytecode subs with native code -> classify per-address with is_bytecode_stub.

Usage:
  py -3 native_floor.py            # ranked match table + completeness summary
  py -3 native_floor.py --toml     # emit the native label block (canonical names)
"""
import sys, difflib
from collections import Counter, deque
from pathlib import Path
# reuse the proven primitives from the ROTK1 toolbox (sibling repo); koei-nes graduation candidates.
sys.path.insert(0, r"C:\Users\Chris.Isaacson\ro3k-decompiler\tools")
import handler_match as H   # bank15(), signature(), load_names()
import disasm6502 as D      # OPS / MODE_LEN / addressing-mode consts

LEMP_ROM  = r"C:\Users\Chris.Isaacson\LEmp-decompiler\Empereur, L' (USA).nes"
LEMP_TOML = r"C:\Users\Chris.Isaacson\LEmp-decompiler\mesen-labels.toml"
# Oracle = NA2 (L'Empereur's base title; closest reset match; fully named, CPU-addr-keyed fixed region).
ORA_ROM  = r"C:\Users\Chris.Isaacson\na2-decompiler\Nobunaga's Ambition II (USA).nes"
ORA_TOML = r"C:\Users\Chris.Isaacson\na2-decompiler\mesen-labels.toml"
ORA_STUB = bytes([0x20, 0x14, 0xE4])             # NA2 vm_entry stub (to exclude oracle bytecode subs)

VM_STUB = bytes([0x20, 0x09, 0xE5])              # L'Empereur vm_entry stub; a bytecode sub begins with this
HANDLER_LO, HANDLER_HI = 0xED1E, 0xEE1E          # VM opcode-handler address tables (256 entries)
VM_SEEDS = {0xE509, 0xE54D}                       # vm_entry, dispatcher
# SYSCALL (RESOLVED recon #1): L'Empereur relocates the private syscall vector to $FFDE (GemFire-aligned),
# NOT NA2/BK's $FFF8 (which reads $0000 here) -- ENGINE-vs-CONFIG divergence. Entry trampolines $EF1E
# (22-byte param struct copy, NA2 $EE29 analog) + $EF3E (id in A, NA2 $EE49 analog) fake-BRK to ($FFDE).
SYSCALL_VEC   = 0xFFDE                             # ($FFDE) = $F961 dispatcher
SYSCALL_TABLE = 0xF98B                             # raw 2-byte handler addresses; id0=$F500 reset
SYSCALL_SLOTS = 27                                 # id 0-26 (vs NA2 31, GemFire 28)
SYSCALL_TRAMPS = {0xEF1E, 0xEF3E, 0xF984}         # param-copy entry, simple entry, central return
# NOTE: no EXTOP table hardcoded yet -- the $B7 ext-op sub-dispatcher, if present, surfaces via reach.

# BYTECODE-REACHABLE native leaves (the bottom-up completion): native subs called ONLY from bytecode
# via CALL_abs -- never from a native JSR, so the vector/handler/JSR-census seeds miss them. Extracted
# from the {native} CALL targets across ALL decompiled banks (0-17, 30, 31), not just the fixed banks --
# app banks call more record/field helpers. Seeding them closes the floor: reach_from expands each +
# classifies vs NA2. ($D43B alone has 42 bytecode callers.)
BYTECODE_LEAVES = {
    # fixed-bank leaves (banks 30/31)
    0xD38D, 0xD460, 0xD4CD, 0xD7B0, 0xD7D1, 0xD7F3, 0xDCD6, 0xDCF6, 0xDD1F,
    0xDD79, 0xDDCA, 0xDE0F, 0xDE2C, 0xDE3B, 0xDE6E, 0xDE77, 0xF3A3, 0xF423,
    # app-bank leaves (record/field helpers reached from banks 0-17)
    0xD383, 0xD3B6, 0xD402, 0xD43B, 0xD47C, 0xD53C, 0xD5A3, 0xD61B, 0xDC6B,
}

def is_bytecode_stub(buf, addr):
    o = addr - 0xC000
    return 0 <= o <= 0x4000 - 3 and buf[o:o+3] == VM_STUB

def jsr_targets(buf):
    c = Counter()
    for i in range(0x4000 - 2):
        if buf[i] == 0x20:
            t = buf[i+1] | buf[i+2] << 8
            if 0xC000 <= t <= 0xFFFF:
                c[t] += 1
    return c

def vm_op_handlers(buf):
    """VM opcode handlers reached via JMP($00) after a table lookup -- a JSR census can't see them,
    so seed straight from the handler tables for complete native coverage."""
    lo, hi = HANDLER_LO - 0xC000, HANDLER_HI - 0xC000
    return set(buf[lo+i] | buf[hi+i] << 8 for i in range(256))

def vectors(buf):
    return {  # NMI/RESET/IRQ at $FFFA + the PRIVATE syscall vector at $FFDE (not $FFF8 for this title)
        buf[0x3FFA] | buf[0x3FFB] << 8: "nmi_handler",
        buf[0x3FFC] | buf[0x3FFD] << 8: "reset_handler",
        buf[0x3FFE] | buf[0x3FFF] << 8: "irq_brk_handler",
        buf[SYSCALL_VEC - 0xC000] | buf[SYSCALL_VEC - 0xC000 + 1] << 8: "syscall_dispatch",
    }

def syscall_handlers(buf):
    """The private syscall vector ($FFDE->$F961) makes the dispatcher + every table handler +
    the entry trampolines natively reachable/seedable."""
    t = SYSCALL_TABLE - 0xC000
    out = set(SYSCALL_TRAMPS)
    for i in range(SYSCALL_SLOTS):
        a = buf[t + 2*i] | buf[t + 2*i + 1] << 8
        if 0xC000 <= a <= 0xFFFF:
            out.add(a)
    return out

def reach_from(buf, seeds):
    """Recursive-descent reachable native subs from seed entries: follow JSR/JMP-abs/branches; stop a
    block at rts/rti/indirect-jmp/data/bytecode-stub. Following real control flow (not a flat scan)
    avoids picking up in-bytecode-body `20 lo hi` data bytes as phantom subs."""
    subs = set(a for a in seeds if 0xC000 <= a <= 0xFFFF and not is_bytecode_stub(buf, a))
    seen, work = set(), deque(subs)
    while work:
        a = work.popleft()
        if a in seen or not (0xC000 <= a <= 0xFFFF):
            continue
        seen.add(a)
        i = a - 0xC000
        while 0 <= i < 0x4000:
            op = buf[i]
            if op not in D.OPS:
                break
            _mn, mode = D.OPS[op]; ln = 1 + D.MODE_LEN[mode]
            if i + ln > 0x4000:
                break
            tgt = (buf[i+1] | buf[i+2] << 8) if ln == 3 else None
            if op == 0x20 and tgt is not None:
                if 0xC000 <= tgt <= 0xFFFF and not is_bytecode_stub(buf, tgt) and tgt not in subs:
                    subs.add(tgt); work.append(tgt)
            elif mode == D.REL:
                work.append((i + ln + ((buf[i+1] ^ 0x80) - 0x80) + 0xC000) & 0xFFFF)
            if op in (0x60, 0x40):
                break
            if op == 0x4C:
                if tgt is not None and 0xC000 <= tgt <= 0xFFFF and not is_bytecode_stub(buf, tgt):
                    work.append(tgt)
                break
            if op == 0x6C:
                break
            i += ln
    return subs

def native_subs(buf):
    """Complete native-sub set = recursive-descent reach UNION JSR-census, both filtered to exclude
    bytecode-sub starts (is_bytecode_stub) and DATA phantoms ($FF padding / strings)."""
    seeds = set(vectors(buf)) | vm_op_handlers(buf) | syscall_handlers(buf) | VM_SEEDS | BYTECODE_LEAVES
    jt = jsr_targets(buf)
    census = set(a for a in jt if not is_bytecode_stub(buf, a))
    subs = reach_from(buf, seeds | census)
    subs |= census
    def is_code(a):
        sig = H.signature(buf, a, cap=16)
        return sig and sig.count(".db") <= 0.4 * len(sig)
    subs = set(a for a in subs if not is_bytecode_stub(buf, a) and is_code(a))
    return sorted(subs), jt

def is_ora_stub(buf, a):
    o = a - 0xC000
    return 0 <= o <= 0x4000 - 3 and buf[o:o+3] == ORA_STUB

def oracle():
    """NA2 fixed-region native subs as the naming oracle: every CPU-addr label in $C000-$FFFF that is
    NOT an NA2 bytecode stub and decodes as code, with its signature."""
    buf = H.bank15(ORA_ROM)
    names = H.load_names(ORA_TOML)
    sig = {}
    for a in names:
        if 0xC000 <= a <= 0xFFFF and not is_ora_stub(buf, a):
            s = H.signature(buf, a)
            if len(s) >= 3:
                sig[a] = s
    return buf, names, sig

def best_match(sig, ora_sig):
    best_a, best = None, 0.0
    for oa, os in ora_sig.items():
        sc = difflib.SequenceMatcher(None, sig, os).ratio()
        if sc > best:
            best, best_a = sc, oa
    return best_a, best

def analyze():
    lm = H.bank15(LEMP_ROM)
    subs, jt = native_subs(lm)
    _o, ora_names, ora_sig = oracle()
    rows = []
    for a in subs:
        sig = H.signature(lm, a)
        if len(sig) < 3:
            rows.append((a, len(sig), None, 0.0, jt.get(a, 0))); continue
        oa, sc = best_match(sig, ora_sig)
        rows.append((a, len(sig), oa, sc, jt.get(a, 0)))
    return rows, ora_names

def main():
    rows, ora_names = analyze()
    if "--toml" in sys.argv:
        print("# --- L'EMPEREUR fixed-bank NATIVE floor (GENERATED by tools/native_floor.py; oracle = NA2) ---")
        print("# >=.90 inherit NA2 canonical name (relocated-identical); .70-.90 diverged (verify);")
        print("# <.70 L'Empereur-specific/reworked (read before naming). Sorted by address.")
        seen = {}
        for a, ln, oa, sc, callers in sorted(rows):
            if ln < 3:
                continue
            nm = ora_names.get(oa) if oa else None
            if sc >= 0.90 and nm:
                key = nm if nm not in seen else f"{nm}_{a:04x}"; seen[nm] = 1
                c = f"== NA2 {nm} (${oa:04X}) score {sc:.2f} relocated-identical; {callers} callers"
            elif sc >= 0.70 and nm:
                key = nm if nm not in seen else f"{nm}_{a:04x}"; seen[nm] = 1
                c = f"~ NA2 {nm} (${oa:04X}) score {sc:.2f} diverged (reloc); same function -- verify; {callers} callers"
            else:
                key = f"native_{a:04x}"; best = ora_names.get(oa, '-') if oa else '-'
                c = f"L'Empereur-specific native (best NA2 {best} {sc:.2f}); {callers} callers -- READ before naming"
            print(f'"0x{a:04X}" = {{ name = "{key}", comment = "{c}" }}')
        return
    print(f"{'LEMPaddr':>8} {'len':>4} {'callers':>7} {'NA2':>6} {'score':>6}  verdict / inherited name")
    print("-" * 96)
    shared = near = spec = 0
    for a, ln, oa, sc, callers in sorted(rows, key=lambda r: -r[3]):
        nm = ora_names.get(oa, f"sub_{oa:04x}") if oa else "-"
        if sc >= 0.90:   tag = "=="; shared += 1
        elif sc >= 0.70: tag = "~ "; near += 1
        else:            tag = "!!"; spec += 1
        oa_s = f"${oa:04x}" if oa else "  -  "
        print(f"${a:04x} {ln:>4} {callers:>7} {oa_s:>6} {sc:>6.2f}  {tag} {nm}")
    print("-" * 96)
    thunks = sum(1 for a, ln, *_ in rows if ln < 3)
    real_spec = spec - thunks
    total = len(rows)
    jsr_reached = sum(1 for a, *_ , c in rows if c > 0)
    print(f"L'Empereur fixed-bank native subs: {total} total ({jsr_reached} JSR-reached + vector/handler seeds)")
    print(f"  SHARED w/ NA2 (>=.90): {shared}   NEAR (.70-.90): {near}")
    print(f"  L'EMPEREUR-SPECIFIC (<.70): {real_spec} real  +  {thunks} thunks/<3-op")
    print(f"  => named canonically (>=.70): {shared+near} / {total-thunks} fingerprintable native subs")

if __name__ == "__main__":
    main()

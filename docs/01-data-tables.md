---
status: active
created: 2026-07-02
---
# L'Empereur — data tables & strings (data-walk reference)

> Ground-truth reference for the ROM's data pools, extracted by the data-walk (`dump_data.py`;
> KOEI UI text = NUL-terminated ASCII). Physical bank = `copy_from_bank` bank value **& 0x1F**.
> This is what makes the app-bytecode banks legible — record types, names, and command prompts.

## Data-bank map (physical 8K bank ← bank value)

| bank value | phys bank | file | contents |
|---|---|---|---|
| 250 (`$FA`) | 26 | `0x34000` | **record name + init-data tables** (countries / cities / generals) |
| 244 (`$F4`) | 20 | `0x28000` | **message pool** (diplomacy / trade / command prompts) + menu layout |
| 243 (`$F3`) | 19 | `0x26000` | font / charmap + scene headers (`load_scene $A004`) |

## Record schema (resolved from the name pools)

| record base (RAM) | stride | entity | name table (bank 250) | field/init data |
|---|---|---|---|---|
| `$6005` | 15 | **generals** | `$A65A` stride 17 | `$A669` (`general_field`) |
| `$7068` | 18 | **countries** | `$A004` stride 10 | `$A00D` (`country_byte`) |
| `$7176` | 28 | **cities** | `$A09A` stride 32 | `$A0A7` (`city_field`), `$A0B2` 7-byte (`city_data7`) |

**Schema is GENERIC on purpose.** The `lemp` entry in `koeivm/vm_decompile.py` (`LEMP_FIELDS = {}`)
renders every record word field as `field_N` — *not* NA1's names. The arg record is a mix of all three
types, so a wrong offset guess mislabels all of them (the old NA1 fallback did exactly that: bogus
`->debt`). **Pin an offset ONLY when a command handler is shown modifying it (the app-bank command-walk).**

### Candidate fields from the manual (`docs/L'Empereur.pdf`) — names/ranges, NOT yet offset-pinned

Notation in the manual: `<>` = attribute a command *reads*, `*` = data a command *affects*.

- **General** (`$6005`, stride 15) — officer attributes: **Leadership** (`<>` Speech), **Loyalty**
  (`*` Reward), plus Ability/Rank; each general commands Soldiers / Horses / Guns (reserves). Napoleon's
  family (Joseph, Louis, Jerome, Eugene…) are special officers.
- **City** (`$7176`, stride 28) — the domestic record. Resources (word): **Gold**, **Food**,
  **Materials**, **Soldiers**, **Guns/Artillery**, **Horses**, **Ships**. %/level (byte): **Morale**,
  **Training**, **Industry**, **Trade** (commercial worth), **Farming**, **Hospital**, Weapons-Factory
  level. Plus commander (officer ptr) + owner nation.
- **Country** (`$7068`, stride 18) — national treasury **Gold/Food/Materials**, **Political Ability**,
  **Hostility**, alliance/friendship/at-war flags.

### Command → attribute map (naming key for the app-bank command handlers)

| command | reads `<>` | affects `*` |
|---|---|---|
| Invest·Industry / Commerce / Agriculture / Medical | Financial/Building | Industry·Materials / Trade / Farming·Food / Hospital |
| Recruit (5 food/sol) · Horse (5 gold/horse) | — | Soldiers / Horses |
| Speech / Reward / Training | Leadership / — / — | Morale / Loyalty / Training |
| Tax / Supply / Give | Supplies | Food·industry·trade·farming (Tax harms them) |
| Alliance / Friendship / Declare War / Trade | Political Ability | Hostility / diplomacy flags |

## Names — countries (15, `$A004` stride 10)
France, Holland, Bavaria, Denmark, Turkey, Italy, Venice, Naples, Portugal, Sweden, Spain, Prussia,
Russia, Austria, England.

## Names — cities (~46, `$A09A` stride 32)
Dublin, Edinburgh, Liverpool, Bristol, London, Christiania, Stockholm, Copenhagen, Amsterdam, Lubeck,
Berlin, Warsaw, Konigsberg, StPetersburg, Minsk, Smolensk, Moscow, Kiev, Klausenburg, Bucharest,
Budapest, Vienna, Prague, Munich, Frankfurt, Lille, St.Malo, Paris, Bordeaux, Lyon, Marseilles, Milan,
Florence, Venice, Sarajevo, Belgrade, Rome, Naples, Istanbul, Athens, Corunna, Lisbon, Gibraltar,
Madrid, Saragossa, Barcelona.

## Names — generals (~80, `$A65A` stride 17)
Napoleon, Joseph, Lucien, Louis, Jerome, Eugene, Serurier, Carnot, Berthier, Talleyrand, Moncey, Barras,
Lefebvre, Augereau, La Mette, Massena, Fouche, Bernadotte, Victor, St.Cyr, Dupont, D'Erlon, MacDonald,
Grouchy, Bessieres, Milhaud, Murat, Desaix, Mortier, Soult, Ney, Friant, Lannes, Vandamme, Cambronne,
Kellermann, Suchet, Davout, Bourrienne, … (Napoleon's marshalate).

## Fixed-bank UI strings (`$DF16-$DF57`, bank 30)
`str_yn_prompt "(Y/N)?"` · `str_yes "Y"` · `str_no "N"` · `str_ok "OK"` · `str_range_prompt "(%d-%d)?"`
· debug: `str_dbg_c0pc "C0PC = %d"`, `str_dbg_bk4 "bk4=%d"`, `str_dbg_bk5 "bk5=%d"` (→ `$C003 fatal_hang`
is a developer crash screen).

## Message pool (bank 244 / phys 20) — 42 entries, indexed by a pointer table at `$A000`
Diplomacy / trade / command prompts (`%s`/`%d` are `vsprintf` args):

| # | text | # | text |
|---|---|---|---|
| 0 | How much | 21 | Number of ships : %d |
| 2 | Distribute how much | 22 | Send how many ships |
| 3 | Country's %s is not enough | 24 | Build how many ships |
| 5 | No %s in that country | 25 | Scrap how many |
| 9 | That country has a shortage of %s | 26 | Position in which city? |
| 10 | Import how much | 28 | City artillery : %d |
| 11 | Use how much gold | 29 | %s has become a new commander |
| 13 | our trade talks were useless... | 31 | Dispatch to which city? |
| 16 | Export how much | 32 | Make a tax payment |
| 17 | Sell for how much | 33 | Make the city a supply base |
| 18 | Issue command to which city? | 35-40 | flavor (family letters to Napoleon) |
| 19 | That city's command has ended | 41 | %d ship has arrived in the harbor |
| 20 | Transport to which city? | | |

These prompts map ~1:1 to player commands (trade, import/export, transport, build/scrap ships,
position artillery, appoint commander, tax, supply base) — a naming key for the app-bank command handlers.

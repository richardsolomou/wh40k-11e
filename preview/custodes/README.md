# Custodes codex

This branch replaces only the Adeptus Custodes catalogue and its datacards, for use as overlays until BSData publishes its own codex catalogue. Points come from the official Munitorum Field Manual 1.6, published on 14 October 2026; this branch supplies none. The main and Space-Marine-Codex branches remain upstream tracking branches.

## MFM 1.6 release

The generated preview was reconciled with MFM 1.6 by hand after the build:

- Every unit and enhancement price the preview shares with MFM 1.6 already matched it. The community copy caps were removed; MFM requisition rows price repeat copies, and each datasheet carries the battle-size unit limit BSData encodes for every faction: 3 (2 in Incursion), doubled for Battleline and Dedicated Transports, 1 for Epic Heroes. Prosecutor Squads take the Battleline limit under Null Maiden Vigil.
- The provisional Leader and Support lists match MFM 1.6 for every codex datasheet.
- Aleya, Valerian, Venerable Contemptor Dreadnought, Venerable Land Raider, Ares Gunship and Orion Assault Dropship, which MFM 1.6 still prices, keep their index datasheets, identities and Game Datacards cards. Aleya and Valerian lead the codex units MFM 1.6 lists for them.
- MFM 1.6 also prices three-model Legends units: Custodian Guard Sodality with Adrasite Spears, with Pyrithite Spears, and Sagittarum Custodians Sodality. No source here provides their datasheets, and the index units have different compositions, so they are not offered.

## Sources

The authored input in `community.json` was extracted from [orpheax/custobuilder](https://github.com/orpheax/custobuilder/tree/dcaaab65d527a147a77931ea3045968d883bab53), pinned to commit `dcaaab65d527a147a77931ea3045968d883bab53`. Its [public builder](https://orpheax.github.io/custobuilder/) and notes distinguish confirmed V2 transcriptions from assumptions. The extracted input has SHA-256 `3094e6bac9202a2238f93b92e6ae77163e141b35f56e94f18351fb9943a02762`; the pinned JavaScript has SHA-256 `646c135e1e68217770e366e940c4387f0347a9040823954bbeb23e7e44a66c6b`.

Rules, profiles and equipment were visually checked against the 30-page scanned codex excerpt, SHA-256 `89f30abff730e744f69da4054300f66e6a8ea6e22d9b23b604e8cca2b425dc4f`. The scan is not committed. Army rules and six ka’tah cards were also checked against [Games Workshop’s published preview](https://www.warhammer-community.com/en-gb/articles/vygelghy/new-army-rules-from-codex-adeptus-custodes/). These sources are not a complete codex or an official points publication.

Local supplementary references were also checked: the 18-page datasheet PDF (SHA-256 `6a522cc16f405fda14b6bc04e562ba2ae17150780303bde5bfd2a2b2d95c2197`) and 29-page army reference (SHA-256 `11278203fe0e6645c06959f329a26064837fb27c01324cf9402f8a0fc4e03cec`). Both are unofficial summaries with no points or attachment table; asterisks mark fields inferred from sibling datasheets. These PDFs are not committed.

Preview prices use the user-supplied [pricing sheet](https://docs.google.com/spreadsheets/d/1ILkYgoxtbNGMOejKReJDRg8PoW1AvxWZvkVQ80ua_rE/edit?gid=0), captured on 10 October 2026 with CSV SHA-256 `b8c605936ffb1bb4c111cd3f6e2a7c69e09c6b6f86eca1adb825f48488428e63`. The normalized authored input is `pricing.json`. This sheet takes precedence over conflicting builder prices: Achillus is 230, Galatus is 220, and Rhino is 70 (80 from the fourth copy). Shield-Captain shield loadouts add 25 points. All 29 enhancement prices agree; printed enhancement names are retained where the sheet abbreviates or mistranscribes them.

The publisher’s [live Field Manual](https://mfm.warhammer-community.com/en/adeptus-custodes) was also checked. Its Custodes v1.5 page still lists the earlier Guard composition of four/five models and Blade Champion at 110 points, rather than this preview’s three-model Guard and 175-point Champion. Its Rhino/Galatus prices and Leader table therefore cannot fill this preview’s missing data.

## Build and overlay paths

Run `python3 -B preview/custodes/build.py`, then `python3 -B -m unittest discover -s preview/custodes -p 'test_*.py'`. The generator reads its baseline directly from commit `3988a8bdd210f9d31ea5b6782d0016688ccb6815` and preserves existing datasheet and detachment IDs where their identities remain unambiguous. Renamed Guard and Sisters units retain their earlier identities; the two Aquilon and two Venatari datasheets have distinct identities.

Pin the definitions and datacards from the same committed revision as overlays:

| Source | Repository path | Destination path |
| --- | --- | --- |
| definitions | `Imperium - Adeptus Custodes.json` | `Imperium - Adeptus Custodes.json` |
| datacards | `11th/gdc/adeptuscustodes.json` | `11th/gdc/adeptuscustodes.json` |

The generator output has 27 datasheets, 13 detachments and 29 enhancements/upgrades, and the release adds the six index datasheets above. Its points file is no longer published. The build and its tests rewrite the published files and drop the reconciliation above.

## Known gaps

- Sisters support the four-, five-, nine- and ten-model compositions MFM 1.6 prices.
- Detachment and enhancement text includes community summaries. The generator corrects the scanned name Leonine Ferocity, Eagle’s Eye wording, and Moritoi stratagem timing.
- Superhuman Focus and Gilded Champion have per-unit/model limits the battle tracker cannot represent. In Auramite Clad, Vigil Unending and Honoured Interred have phase-dependent turn restrictions it cannot represent. Their text is retained, but their executable battle cards remain unavailable.
- Ka’tah readiness, activated abilities and conditional movement/OC effects do not have automatic battle-state transitions. Combat wording and the Orb’s Blinding Light keyword still need complete engine coverage.

Verify construction, saved selections, repeat prices, defaults and references in the consuming application before publishing.

## Automatic benefit audit

Permanent benefits use catalogue modifiers and rule links. Conditional and activated effects retain their conditions instead of changing the permanent datasheet. The faction reference groups Psychic Null under Daughters of the Abyss, as printed. Datasheets link the Sisters’ own protection and their granted aura separately, so their 3+ psychic protection cannot extend to nearby Custodes. Ka’tah cards retain each printed trigger, target and effect, with supported keyword markup and lists. Aquila Commander is linked only to Trajann and the three Shield-Captain datasheets; its CP gain requires that model to be the Warlord.

| Source | Evaluated benefit |
| --- | --- |
| Printed invulnerable saves | An `InSv` characteristic on every applicable unit; Sisters without one retain none |
| Vexilla on Sentinel Guard, Guard, Wardens and Allarus | +1 OC once for the unit, only while equipped |
| Knight-Centura’s Seeker’s Instincts | +2" Move in the evaluated roster |
| Eagle’s Eye | +1 W; the activated 3+ save does not replace the permanent 4+ save |
| Not a Shell Wasted | +1 ranged Attacks |
| Memento Moritoi | +1 melee Attacks, Strength and Damage |
| Emperor’s Light and Auriferous Orb | Their additional weapon profiles appear only while equipped |
| Auric Exemplar, Flawless Bladework and From the Hall of Armouries | Cleave 1, Sustained Hits 1 and Devastating Wounds on the bearer’s melee weapons |
| Genalchemic Warding and Augury Uplink | Feel No Pain 5+ |
| Shroud of the Hidden Blade | Stealth and Lone Operative |
| Emissaries Imperatus | Fights First on Custodes units, excluding Anathema Psykana |
| Null Maiden Vigil | Battleline on Prosecutors and the permitted Sisters Warlord choice |
| Core and army abilities | Links to their actual rule definitions; Aegis mortal protection and Daughters’ psychic protection retain their restrictions |

The remaining 18 enhancements/upgrades were inventoried: Bane of Abominations, Castellan’s Mark, Unstoppable Destroyer, Sally Forth, Auric Eagle, Pareldor’s Caducatrix, Edge of the Blade, Radiant Mantle, Inspirational Exemplar, Superior Creation, Arae-Shrike, Celeritous Sentries, Lightning Descent, Leonine Ferocity, Combat Deployment, Anti-Gravitic Mobility, Oblivion Knight and Huntress’ Eye. Their effects change a roll, movement permission, target interaction or activated battle state rather than a permanent characteristic. The other 11 detachment rules and six favoured ka’tahs were inventoried on the same basis; Moritoi’s +2 OC requires starting-strength state, and Grav-Assault’s 4+ save applies only to ranged attacks. Neither is an unconditional datasheet change.

Consumer verification covers all 27 offered units, 39 priced compositions, 51 equipment selections, 155 zero/one/multiple-copy price scenarios, and 16 equipment resize cycles. It also checks saved enhancement selections, unselected controls, sibling faction restrictions, nested enhancement uniqueness and mutually exclusive Shield Hosts. This verifies the encoded permanent benefits; the known gaps above still block release readiness.

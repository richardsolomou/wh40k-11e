import json
import unittest

import build


class CustodesPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build.build()
        cls.catalogue = json.loads((build.ROOT / 'Imperium - Adeptus Custodes.json').read_text())['catalogue']
        cls.points = json.loads((build.ROOT / 'data/adeptus-custodes.yaml').read_text())
        cls.cards = json.loads((build.ROOT / '11th/gdc/adeptuscustodes.json').read_text())

    def unit(self, name):
        return next(e for e in self.catalogue['sharedSelectionEntries'] if e['name'] == name)

    def test_all_units_with_sheet_prices_are_offered(self):
        self.assertEqual([e['name'] for e in self.catalogue['entryLinks'] if e.get('hidden')],
                         [])

    def test_wardens_have_verified_two_and_three_model_prices(self):
        unit = next(u for u in self.points['units'] if u['name'] == 'Custodian Wardens')
        self.assertEqual(unit['pricing'], [
            {'range': '[1,1]', 'costs': [{'models': 2, 'points': 200}, {'models': 3, 'points': 295}]},
            {'range': '[2,2]', 'costs': [{'models': 2, 'points': 230}, {'models': 3, 'points': 325}]},
            {'range': '[3,3]', 'costs': [{'models': 2, 'points': 230}, {'models': 3, 'points': 325}]},
        ])

    def test_rhino_optional_missile_does_not_grant_vexilla_bonus(self):
        rhino = self.unit('Anathema Psykana Rhino')
        optional = next(e for e in rhino['selectionEntries'] if e['name'] == 'Hunter-killer Missile')
        self.assertEqual([(c['type'], c['value']) for c in optional['constraints']], [('min', 0), ('max', 1)])
        self.assertNotIn('Vexilla', [e['name'] for e in rhino['selectionEntries']])

    def test_shield_loadouts_pay_the_sheet_equipment_surcharge(self):
        body = self.unit('Shield-Captain')['selectionEntries'][0]
        self.assertEqual([e['costs'][0]['value'] for e in body['selectionEntryGroups'][0]['selectionEntries']], [25, 25, 0, 0])

    def test_blade_champion_equipment_has_all_three_printed_profiles(self):
        body = self.unit('Blade Champion')['selectionEntries'][0]
        self.assertEqual([p['name'] for p in body['selectionEntries'][0]['profiles']],
                         ['Vaultswords – Behemor', 'Vaultswords – Hurricanis', 'Vaultswords – Victus'])

    def test_optional_shield_does_not_grant_its_ability_to_every_loadout(self):
        self.assertNotIn('Praesidium Shield', [p['name'] for p in self.unit('Shield-Captain')['profiles']])

    def test_guard_keeps_its_existing_pick_identity(self):
        guard = next(e for e in self.catalogue['entryLinks'] if e['name'] == 'Custodian Guard Sodality')
        self.assertEqual(guard['id'], 'd0ce-f2d3-358f-4530')

    def test_anathema_units_do_not_gain_the_custodes_faction_keyword(self):
        self.assertNotIn('Adeptus Custodes', [c['name'] for c in self.unit('Prosecutor Squad')['categoryLinks']])

    def test_mixed_turn_timing_stays_reference_only(self):
        card = next(s for s in self.cards['stratagems'] if s['name']['en'] == 'Honoured Interred')
        self.assertEqual((card['when']['en'], card['turn']), ('Your Shooting phase or the Fight phase', None))

    def test_invulnerable_saves_are_actual_unit_characteristics(self):
        values = self.unit('Contemptor-Achillus Dreadnought')['profiles'][0]['characteristics']
        self.assertIn({'name': 'InSv', 'typeId': build.identity('Unit/InSv'), '$text': '5+'}, values)

    def test_equipped_vexilla_changes_objective_control_once_for_the_unit(self):
        vexilla = next(e for e in self.unit('Custodian Guard Sodality')['selectionEntries'] if e['name'] == 'Vexilla')
        self.assertEqual(vexilla['modifiers'], [{'type': 'increment', 'field': build.identity('Unit/OC'),
            'value': 1, 'scope': 'unit', 'affects': 'self.entries.group.recursive.profiles.Unit'}])

    def test_enhancement_uniqueness_counts_nested_selections(self):
        eagle = self.unit('Eagle’s Eye')
        cap = next(c for c in eagle['constraints'] if c['type'] == 'max')
        self.assertEqual((cap['scope'], cap['value'], cap['includeChildSelections']), ('roster', 1, True))

    def test_extra_enhancement_weapon_is_equipped_as_a_profile(self):
        light = next(p for p in self.unit('Emperor’s Light')['profiles'] if p['typeName'] == 'Melee Weapons')
        self.assertEqual({c['name']: c['$text'] for c in light['characteristics']},
            {'Range': 'Melee', 'A': '3', 'WS': '2+', 'S': '5', 'AP': '-2', 'D': '2', 'Keywords': 'Extra Attacks'})

    def test_core_and_army_rules_are_linked_not_inert_inline_entries(self):
        guard = self.unit('Custodian Guard Sodality')
        self.assertEqual([link['name'] for link in guard['infoLinks']],
            ['Deep Strike', 'Aegis of the Emperor', "Martial Ka'tah", 'Fights First'])

    def test_take_and_hold_remains_one_force_disposition(self):
        card = next(d for d in self.cards['detachments'] if d['name']['en'] == 'Aquilan Shield')
        self.assertEqual(card['forceDispositions'], [{'name': {'en': 'Take and Hold'}}])

    def test_psychic_null_is_granted_by_daughters_not_a_separate_army_rule(self):
        self.assertEqual([r['name']['en'] for r in self.cards['rules']['army']],
                         ['Aegis of the Emperor', 'Aquila Commander', 'Daughters of the Abyss', "Martial Ka'tah"])
        daughters = next(r for r in self.cards['rules']['army'] if r['name']['en'] == 'Daughters of the Abyss')
        self.assertIn('Psychic Null (Aura)', daughters['rules'][0]['text']['en'])

    def test_anathema_datasheets_link_the_granted_aura_as_an_ability(self):
        for name in ['Knight-Centura', 'Prosecutor Squad', 'Vigilator Squad', 'Witchseeker Squad', 'Anathema Psykana Rhino']:
            with self.subTest(unit=name):
                links = self.unit(name)['infoLinks']
                aura = next(link for link in links if link['name'] == 'Psychic Null (Aura)')
                self.assertEqual(aura['type'], 'profile')
                card = next(s for s in self.cards['datasheets'] if s['name']['en'] == name)
                self.assertEqual(card['abilities']['faction'], [{'name': {'en': 'Daughters of the Abyss'}}])

    def test_katah_cards_use_supported_keyword_markup_and_lists(self):
        katah = next(r for r in self.cards['rules']['army'] if r['name']['en'] == "Martial Ka'tah")['rules'][0]['text']['en']
        self.assertNotIn('<code>', katah)
        self.assertIn('<k>[LETHAL HITS: MONSTER/VEHICLE]</k>', katah)
        self.assertIn('- BS.\n- <b>Hit rolls</b> and <b>wound rolls</b>.', katah)

    def test_aquila_commander_is_only_linked_to_the_four_printed_commanders(self):
        self.assertEqual([e['name'] for e in self.catalogue['sharedSelectionEntries']
                          if any(link['name'] == 'Aquila Commander' for link in e.get('infoLinks', []))],
                         ['Trajann Valoris', 'Shield-Captain', 'Shield-Captain in Allarus Terminator Armour',
                          'Shield-Captain on Dawneagle Jetbike'])

    def test_army_rule_links_respect_faction_and_grav_vehicle_exclusions(self):
        grav = {'Pallas Grav-Attack', 'Coronus Grav-Carrier', 'Caladius Grav-Tank', 'Caladius Annihilator Grav-Tank'}
        for entry in self.catalogue['sharedSelectionEntries']:
            if entry['type'] != 'unit':
                continue
            with self.subTest(unit=entry['name']):
                custodes = 'Adeptus Custodes' in [c['name'] for c in entry['categoryLinks']]
                linked = [link['name'] for link in entry['infoLinks']]
                self.assertEqual('Aegis of the Emperor' in linked, custodes)
                self.assertEqual("Martial Ka'tah" in linked, custodes and entry['name'] not in grav)
                self.assertEqual('Daughters of the Abyss' in linked, not custodes)


if __name__ == '__main__':
    unittest.main()

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
SOURCE = json.loads((HERE / 'community.json').read_text())
PRICING = json.loads((HERE / 'pricing.json').read_text())
for enhancement in SOURCE['ENH']:
    if enhancement['id'] == 'leonine':
        enhancement['name'] = 'Leonine Ferocity'
    if enhancement['id'] == 'eagleeye':
        enhancement['t'] = 'The bearer has +1 W. Once per battle, per army, when attacks are allocated to the bearer, it can have a 3+ invulnerable save until the end of the phase.'
for enhancement in SOURCE['ENH']:
    text = {
        'genal': 'The bearer has the Feel No Pain 5+ ability.',
        'augury': 'This unit has the Feel No Pain 5+ ability.',
        'shroud': 'The bearer has the Stealth and Lone Operative abilities.',
        'exemplar': 'Melee weapons equipped by the bearer have the [CLEAVE 1] ability.',
        'bladework': 'Melee weapons equipped by the bearer have the [SUSTAINED HITS 1] ability.',
        'mantle': 'Attacks that target this unit have -1 to hit rolls.',
        'armouries': 'Melee weapons equipped by the bearer have the [DEVASTATING WOUNDS] ability.',
    }.get(enhancement['id'])
    if text:
        enhancement['t'] = text
for sheet in SOURCE['DSD'].values():
    for ability in sheet['abilities']:
        if ability['text'] == 'Attacks allocated to this model have -1 D.':
            ability['text'] = 'Each time an attack is allocated to this model, subtract 1 from the Damage characteristic of that attack.'
BASE_REVISION = '3988a8bdd210f9d31ea5b6782d0016688ccb6815'
BASE = json.loads(subprocess.check_output(['git', 'show', f'{BASE_REVISION}:Imperium - Adeptus Custodes.json'], cwd=ROOT))['catalogue']
SYSTEM = json.loads(subprocess.check_output(['git', 'show', f'{BASE_REVISION}:Warhammer 40,000.json'], cwd=ROOT))['gameSystem']
PTS = next(c['id'] for c in SYSTEM['costTypes'] if c['name'] == 'pts')
DP = next(c['id'] for c in SYSTEM['costTypes'] if c['name'] == 'Detachment Points')
ENH = next(c['id'] for c in SYSTEM['costTypes'] if c['name'] == 'Enhancements')


def identity(name):
    return 'pc-' + hashlib.sha256(name.encode()).hexdigest()[:24]


def constraints(name, low, high, scope='parent'):
    return [dict(id=identity(f'{name}-{kind}'), type=kind, value=value,
                 field='selections', scope=scope, shared=True,
                 **({'includeChildSelections': True} if scope in {'roster', 'force'} else {}))
            for kind, value in [('min', low), ('max', high)]]


def cost(value, kind=PTS, name='pts'):
    return dict(name=name, typeId=kind, value=value)


def profile(key, name, kind, values):
    return dict(id=identity(key), name=name, typeName=kind,
                characteristics=[dict(name=k, typeId=identity(f'{kind}/{k}'), **{'$text': str(v)})
                                 for k, v in values.items()])


def norm(name):
    return re.sub(r'[^a-z0-9]', '', name.lower().replace('’', "'")).rstrip('s')


def dispositions(name):
    return ['Priority Assets', 'Purge the Foe'] if name == 'Priority Assets and Purge the Foe' else [name]


def save(file, value):
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def build():
    catalogue = {k: copy.deepcopy(v) for k, v in BASE.items()
                 if k not in {'entryLinks', 'categoryEntries', 'sharedProfiles', 'sharedRules',
                              'sharedInfoGroups', 'sharedSelectionEntries', 'sharedSelectionEntryGroups'}}
    catalogue['revision'] = BASE['revision'] + 1
    catalogue['categoryEntries'] = []
    catalogue['sharedSelectionEntries'] = []
    catalogue['entryLinks'] = []
    catalogue['sharedRules'] = []
    catalogue['sharedProfiles'] = []
    categories = {c['name'].lower(): c['id'] for c in SYSTEM['categoryEntries']}

    def category(name):
        key = name.lower()
        if key not in categories:
            categories[key] = identity(f'keyword/{name}')
            catalogue['categoryEntries'].append(dict(id=categories[key], name=name))
        return categories[key]

    def link_category(key, name, primary=False):
        return dict(id=identity(f'{key}/{name}'), name=name, targetId=category(name), primary=primary)

    old_entries = {e['name']: e['id'] for e in BASE['sharedSelectionEntries']}
    old_links = {e['name']: e['id'] for e in BASE['entryLinks']}
    old_detachments = next(e for e in BASE['sharedSelectionEntries'] if e['name'] == 'Detachments')
    old_det_ids = {e['name']: e['id'] for e in old_detachments['selectionEntryGroups'][0]['selectionEntries']}
    det_ids = {d['id']: old_det_ids.get(d['name'], identity(f'detachment/{d["id"]}')) for d in SOURCE['DETS']}
    unique = category('Unique: Shield Host')
    next(c for c in catalogue['categoryEntries'] if c['id'] == unique)['constraints'] = [
        dict(id=identity('one-shield-host'), type='max', value=1, field='selections', scope='force',
             shared=True, includeChildSelections=True,
             message='choose at most one Unique: Shield Host detachment')]
    detachments = []
    for d in SOURCE['DETS']:
        keywords = dispositions(d['fd'])
        if d['unique']:
            keywords.append('Unique: Shield Host')
        detachments.append(dict(id=det_ids[d['id']], name=d['name'], type='upgrade',
                                costs=[cost(d['dp'], DP, 'Detachment Points')],
                                constraints=constraints(f'det/{d["id"]}', 0, 1, 'force'),
                                categoryLinks=[link_category(d['id'], name) for name in keywords]))
    catalogue['sharedSelectionEntries'].append(dict(
        id=old_detachments['id'], name='Detachments', type='upgrade',
        selectionEntryGroups=[dict(id=old_detachments['selectionEntryGroups'][0]['id'], name='Detachments',
                                   selectionEntries=detachments)]))

    enhancements = {}
    for e in SOURCE['ENH']:
        key = identity(f'enhancement/{e["id"]}')
        name = e['name'] + (' (Upgrade)' if e['k'] == 'upg' else '')
        entry = dict(id=key, name=name, type='upgrade',
                     costs=[cost(e['p']), cost(0 if e['k'] == 'upg' else 1, ENH, 'Enhancements')],
                     constraints=constraints(f'enh/{e["id"]}', 0, 1, 'roster'),
                     hidden=True, modifiers=[dict(type='set', field='hidden', value=False,
                          conditions=[dict(type='atLeast', field='selections', scope='force',
                                           childId=det_ids[e['det']], value=1, shared=True,
                                           includeChildSelections=True)])],
                     profiles=[profile(f'enh/{e["id"]}', name, 'Abilities', {'Description': e['t']})])
        permanent = {
            'eagleeye': [('Unit', 'W', 1)],
            'shell': [('Ranged Weapons', 'A', 1)],
            'memento': [('Melee Weapons', field, 1) for field in ['A', 'S', 'D']],
        }
        entry['modifiers'].extend(dict(type='increment', field=identity(f'{kind}/{field}'),
            value=value, scope='root-entry', affects=f'self.entries.group.recursive.profiles.{kind}')
            for kind, field, value in permanent.get(e['id'], []))
        weapon_keywords = {'exemplar': 'Cleave 1', 'bladework': 'Sustained Hits 1', 'armouries': 'Devastating Wounds'}
        if e['id'] in weapon_keywords:
            entry['modifiers'].append(dict(type='append', field=identity('Melee Weapons/Keywords'),
                value=weapon_keywords[e['id']], join=', ', skipIfPresent=weapon_keywords[e['id']], scope='root-entry',
                affects='self.entries.group.recursive.profiles.Melee Weapons'))
        if e['id'] in {'light', 'orb'}:
            values = ({'Range': 'Melee', 'A': 3, 'WS': '2+', 'S': 5, 'AP': -2, 'D': 2, 'Keywords': 'Extra Attacks'}
                      if e['id'] == 'light' else
                      {'Range': '12"', 'A': 3, 'BS': '2+', 'S': 1, 'AP': 0, 'D': 1,
                       'Keywords': 'Anti-non-Monster/Vehicle 2+, Blinding Light, Devastating Wounds'})
            entry['profiles'].append(profile(f'enh/{e["id"]}/weapon', e['name'],
                'Melee Weapons' if e['id'] == 'light' else 'Ranged Weapons', values))
        granted = {'shroud': ['Stealth', 'Lone Operative'], 'genal': ['Feel No Pain 5+'],
                   'augury': ['Feel No Pain 5+']}.get(e['id'], [])
        entry['infoLinks'] = [dict(id=identity(f'enh/{e["id"]}/{name}'), name=name, type='rule',
            targetId=next(r['id'] for r in SYSTEM['sharedRules'] if r['name'] == name)) for name in granted]
        enhancements[e['id']] = entry
        catalogue['sharedSelectionEntries'].append(entry)

    units = {u['id']: u for u in SOURCE['U']}
    units['aquilon_g'] = {**units['aquilon'], 'opts': [units['aquilon']['opts'][0]]}
    units['aquilon_t'] = {**units['aquilon'], 'opts': [units['aquilon']['opts'][1]]}
    system_rules = {r['name']: r['id'] for r in SYSTEM['sharedRules']}

    def core_rule(name):
        return system_rules.get(name) or system_rules[name.rsplit(' ', 1)[0]]

    data = dict(name='Adeptus Custodes', id=BASE['id'], datasheets=[], detachments=[], enhancements=[],
                stratagems=[], rules=dict(army=[], detachment=[]),
                attribution='Unofficial Custodes codex preview transcribed by orpheax/custobuilder')
    points = dict(slug='adeptus-custodes', version=f'custodes-preview-{PRICING["sha256"][:8]}',
                  attribution=f'Community Custodes preview points from the user-supplied pricing sheet ({PRICING["sha256"][:8]})',
                  units=[], detachments=[])
    rules = {
        'Aegis of the Emperor': 'Models in this unit have the Feel No Pain 5+ ability against mortal wounds.',
        'Aquila Commander': 'At the start of the battle round, if a model with this ability is your WARLORD, gain 1CP.',
        'Daughters of the Abyss': 'If this unit has the ANATHEMA PSYKANA keyword, models in this unit have the Feel No Pain 3+ ability against Psychic Attacks.',
    }
    psychic_null = 'While a friendly ADEPTUS CUSTODES unit is within 6" of this unit, models in that unit have the Feel No Pain 5+ ability against Psychic Attacks.'
    catalogue['sharedProfiles'].append(profile('army/Psychic Null (Aura)', 'Psychic Null (Aura)', 'Abilities',
                                              {'Description': psychic_null}))
    katah = ['At the start of your Command phase, friendly ADEPTUS CUSTODES units with this ability become readied. '
             'A readied unit can use one of the ka’tah abilities below at its stated trigger. After using it, that unit is no longer readied.']
    for k in SOURCE['KT']:
        katah.extend([f'### {k["n"]}', f'WHEN: {k["w"]}', f'TARGET: {k["tg"]}',
                      f'EFFECT: {k["e"]}'])
        if k.get('l'):
            katah.append('\n'.join(f'- {line}' for line in k['l']))
    rules["Martial Ka'tah"] = '\n\n'.join(katah).replace('<code>', '<k>').replace('</code>', '</k>')
    for name, text in rules.items():
        catalogue['sharedRules'].append(dict(id=identity(f'army/{name}'), name=name, description=text))
        if name == 'Daughters of the Abyss':
            text += '\n\nANATHEMA PSYKANA units with this ability also have:\n\n**Psychic Null (Aura):** ' + psychic_null
        data['rules']['army'].append(dict(name={'en': name}, rules=[dict(type='text', order=1, text={'en': text})]))

    for key, sheet in SOURCE['DSD'].items():
        u = units[key]
        name = sheet['name']
        old_name = {'guard': 'Custodian Guard', 'prosec': 'Prosecutors', 'witch': 'Witchseekers',
                    'vigil': 'Vigilators'}.get(key, name)
        entry_id = old_entries.get(old_name, identity(f'unit/{key}'))
        pick_id = old_links.get(old_name, identity(f'pick/{key}'))
        copy_prices = {int(n): prices for n, prices in PRICING['units'][key].items()}
        counts = sorted(copy_prices)
        prices = {n: rows[0] for n, rows in copy_prices.items()}
        equipment_prices = PRICING['wargear'].get(key, {})
        kw = list(dict.fromkeys([*sheet['faction'], *sheet['keywords']]))
        if 'SHIELD-CAPTAIN' in u['kw'] and 'SHIELD-CAPTAIN' not in kw:
            kw.append('SHIELD-CAPTAIN')
        cap = max(len(rows) for rows in copy_prices.values())
        catalogue['categoryEntries'].append(dict(id=identity(f'cap/{key}'), name=f'{name} copies', hidden=True,
            constraints=[dict(id=identity(f'cap/{key}/max'), type='max', value=cap, field='selections',
                              scope='force', shared=True, includeChildSelections=True,
                              message=f'preview pricing supports at most {cap} copies of this datasheet')]))
        primary = next((k for k in ['EPIC HERO', 'CHARACTER', 'BATTLELINE', 'DEDICATED TRANSPORT', 'INFANTRY', 'MOUNTED', 'VEHICLE'] if k in kw), 'Infantry')
        unit = dict(id=entry_id, name=name, type='unit',
                    categoryLinks=[*([link_category(key, 'Faction: Adeptus Custodes')] if 'ADEPTUS CUSTODES' in kw else []),
                                   *[link_category(key, k.title(), k == primary) for k in kw],
                                   dict(id=identity(f'caplink/{key}'), name=f'{name} copies', targetId=identity(f'cap/{key}'))],
                    profiles=[profile(f'{key}/stats', name, 'Unit', {('InSv' if k == 'Inv' else k): v for k, v in sheet['stats'].items() if v is not None}),
                              *[profile(f'{key}/ability/{i}', a['name'], 'Abilities', {'Description': a['text']})
                                for i, a in enumerate(sheet['abilities']) if a['name'] not in {'Vexilla', 'Praesidium Shield'}]],
                    infoLinks=[dict(id=identity(f'{key}/rule/{i}'), name=n, type='rule',
                        targetId=identity(f'army/{n}') if n in rules else core_rule(n))
                        for i, n in enumerate([*sheet['core'], *sheet['army']])],
                    selectionEntries=[], selectionEntryGroups=[])
        if 'Daughters of the Abyss' in sheet['army']:
            unit['infoLinks'].append(dict(id=identity(f'{key}/psychic-null'), name='Psychic Null (Aura)',
                type='profile', targetId=identity('army/Psychic Null (Aura)')))
        if 'ADEPTUS CUSTODES' in kw:
            unit['infoLinks'].append(dict(id=identity(f'{key}/fights-first'), name='Fights First',
                type='rule', targetId=system_rules['Fights First'], hidden=True,
                modifiers=[dict(type='set', field='hidden', value=False, conditions=[dict(
                    type='atLeast', field='selections', scope='force', childId=det_ids['emissaries'],
                    value=1, shared=True, includeChildSelections=True)])]))
        if key == 'prosec':
            unit['modifiers'] = [dict(type='add', field='category', value=category('Battleline'),
                conditions=[dict(type='atLeast', field='selections', scope='force', childId=det_ids['nmv'],
                                 value=1, shared=True, includeChildSelections=True)])]
        if key == 'kc':
            unit['modifiers'] = [dict(type='increment', field=identity('Unit/M'), value=2,
                affects='self.profiles.Unit')]

        weapon_profiles = {}
        for kind, weapons in [('Ranged Weapons', sheet['ranged']), ('Melee Weapons', sheet['melee'])]:
            for w in weapons:
                vals = {'Range': w['range'], 'A': w['A'], 'BS' if kind == 'Ranged Weapons' else 'WS': w.get('BS', w.get('WS')), 'S': w['S'], 'AP': w['AP'], 'D': w['D'], 'Keywords': ', '.join(w['kw']) or '-'}
                weapon_profiles.setdefault(norm(w['name']), []).append(profile(f'{key}/{kind}/{w["name"]}', w['name'], kind, vals))

        def weapon(part, prefix):
            part = part.strip().rstrip('.')
            match = re.match(r'(?:(\d+) )?(.+)', part)
            number, label = int(match[1] or 1), match[2]
            profiles = copy.deepcopy([p for weapon_name, rows in weapon_profiles.items()
                                      if weapon_name == norm(label)
                                      or (norm(label) == 'vaultsword' and weapon_name.startswith('vaultsword'))
                                      for p in rows])
            if label == 'Praesidium Shield':
                profiles.extend(profile(f'{prefix}/shield/{i}', a['name'], 'Abilities', {'Description': a['text']})
                                for i, a in enumerate(sheet['abilities']) if a['name'] == label)
            for p in profiles:
                p['id'] = identity(f'{prefix}/{p["id"]}')
            return dict(id=identity(f'{prefix}/{label}'), name=label, type='upgrade', collective=True,
                        profiles=profiles, constraints=constraints(f'{prefix}/{label}', number, number))

        def body(count):
            prefix = f'{key}/{count}'
            default = [p.strip() for p in re.split(r';|,', sheet['equipped'].split(':', 1)[1].strip().rstrip('.'))]
            groups = SOURCE['WG'].get(key, SOURCE['WG'].get('aquilon', []) if key == 'aquilon_t' else [])
            fixed = default[:]
            group_entries = []
            for g in groups:
                if g['k'] == 'tog':
                    continue
                replace = g.get('f') or {'sc': None, 'scall': 'Guardian Spear', 'scjet': 'Salvo Launcher',
                                        'achillus': 'Lastrum Storm Bolter', 'telemon': None,
                                        'pallas': 'Twin Arachnus Blaze Cannon', 'coronus': 'Twin Lastrum Bolt Cannon',
                                        'caladius': 'Twin Lastrum Bolt Cannon', 'annihilator': 'Twin Lastrum Bolt Cannon',
                                        'kc': 'Executioner Greatblade'}.get(key)
                if key == 'aquilon_t':
                    replace = 'Lastrum Storm Bolter'
                if key == 'sc':
                    fixed = []
                elif key == 'telemon':
                    fixed = [p for p in fixed if 'Spiculus' in p]
                elif replace:
                    fixed = [p for p in fixed if norm(re.sub(r'^\d+ ', '', p)) != norm(replace)]
                options = []
                for i, label in enumerate(([g['f']] if g.get('f') else []) + g['c']):
                    label = re.sub(r' \(.*\)$', '', label)
                    label = label.replace('Eternity-pattern Paragon Blade', 'Eternity-pattern Paragon Blade + Praesidium Shield')
                    pieces = re.split(r' \+ | and ', label)
                    options.append(dict(id=identity(f'{prefix}/{g["id"]}/{i}'), name=label, type='upgrade', collective=True,
                                        costs=[cost(sum(p for item, p in equipment_prices.items() if item in label))],
                                        selectionEntries=[weapon(p, f'{prefix}/{g["id"]}/{i}') for p in pieces]))
                group_entries.append(dict(id=identity(f'{prefix}/group/{g["id"]}'), name=g['t'],
                                          defaultSelectionEntryId=options[0]['id'],
                                          constraints=constraints(f'{prefix}/group/{g["id"]}', 1, 1), selectionEntries=options))
            return dict(id=identity(f'{prefix}/body'), name=name, type='model', collective=True,
                        constraints=constraints(f'{prefix}/body', count, count),
                        selectionEntries=[weapon(p, f'{prefix}/default') for p in fixed],
                        selectionEntryGroups=group_entries)

        if len(counts) == 1:
            unit['costs'] = [cost(prices.get(counts[0], 0))]
            unit['selectionEntries'].append(body(counts[0]))
        else:
            options = [dict(id=identity(f'{key}/size/{n}'), name=f'{n} models', type='upgrade',
                            costs=[cost(prices[n])], selectionEntries=[body(n)]) for n in counts]
            unit['selectionEntryGroups'].append(dict(id=identity(f'{key}/sizes'), name='Unit Composition',
                                                    defaultSelectionEntryId=options[0]['id'],
                                                    constraints=constraints(f'{key}/sizes', 1, 1), selectionEntries=options))
        if any(g['k'] == 'tog' and 'Vexilla' in g['c'][0] for g in SOURCE['WG'].get(key, [])):
            unit['selectionEntries'].append(dict(id=identity(f'{key}/vexilla'), name='Vexilla', type='upgrade',
                                                constraints=constraints(f'{key}/vexilla', 0, 1),
                                                modifiers=[dict(type='increment', field=identity('Unit/OC'), value=1,
                                                    scope='unit', affects='self.entries.group.recursive.profiles.Unit')],
                                                profiles=[profile(f'{key}/vexilla/ability', a['name'], 'Abilities', {'Description': a['text']})
                                                          for a in sheet['abilities'] if a['name'] == 'Vexilla']))
        if key == 'rhino':
            missile = weapon('Hunter-killer Missile', f'{key}/optional')
            missile['constraints'] = constraints(f'{key}/optional/Hunter-killer Missile', 0, 1)
            unit['selectionEntries'].append(missile)
        if 'CHARACTER' in kw:
            warlord = copy.deepcopy(next(e for e in BASE['sharedSelectionEntries'] if e['name'] == 'Warlord'))
            warlord['id'] = identity(f'{key}/warlord')
            warlord['constraints'] = constraints(f'{key}/warlord', 0, 1)
            for link in warlord['categoryLinks']:
                link['id'] = identity(f'{key}/warlord/{link["targetId"]}')
            if key == 'trajann':
                warlord['constraints'] = constraints(f'{key}/warlord', 1, 1)
            elif 'ANATHEMA PSYKANA' in kw:
                warlord['hidden'] = True
                warlord['modifiers'] = [dict(type='set', field='hidden', value=False, conditions=[dict(
                    type='atLeast', value=1, field='selections', scope='force', childId=det_ids['nmv'],
                    shared=True, includeChildSelections=True)])]
            unit['selectionEntries'].append(warlord)
        for kind, title in [('enh', 'Enhancements'), ('upg', 'Unit Upgrades')]:
            eligible = [e for e in SOURCE['ENH'] if e['k'] == kind and set(e['req']).issubset(kw)
                        and (not e.get('any') or set(e['any']).intersection(kw))
                        and not set(e.get('not', [])).intersection(kw)
                        and (kind == 'upg' or 'EPIC HERO' not in kw)]
            if eligible:
                unit['selectionEntryGroups'].append(dict(id=identity(f'{key}/{kind}'), name=title,
                    constraints=constraints(f'{key}/{kind}', 0, 1), entryLinks=[dict(
                        id=identity(f'{key}/enh/{e["id"]}'), name=enhancements[e['id']]['name'],
                        type='selectionEntry', targetId=enhancements[e['id']]['id']) for e in eligible]))
        catalogue['sharedSelectionEntries'].append(unit)
        catalogue['entryLinks'].append(dict(id=pick_id, name=name, type='selectionEntry', targetId=entry_id))
        tiers = [dict(range=f'[{copy},{copy}]', costs=[dict(models=n, points=rows[copy - 1])
                 for n, rows in copy_prices.items() if len(rows) >= copy]) for copy in range(1, cap + 1)]
        points['units'].append(dict(name=name, pricing=tiers,
            **({'wargear': [dict(item=item, points=p) for item, p in equipment_prices.items()]} if equipment_prices else {})))
        card = dict(id=entry_id, name={'en': name}, composition=[{'en': sheet['composition']}],
                    loadout={'en': sheet['equipped']}, wargear=[{'en': w} for w in sheet['wargear']],
                    points=[dict(models=str(n), cost=str(p)) for n, p in prices.items()],
                    abilities=dict(faction=[dict(name={'en': n}) for n in sheet['army']],
                                   other=[dict(name={'en': a['name']}, description={'en': a['text']}) for a in sheet['abilities']]))
        if 'Daughters of the Abyss' in sheet['army']:
            card['abilities']['other'].append(dict(name={'en': 'Psychic Null (Aura)'}, description={'en': psychic_null}))
        if sheet.get('transport'):
            card['transport'] = {'en': sheet['transport']}
        data['datasheets'].append(card)

    for d in SOURCE['DETS']:
        data['detachments'].append(dict(id=det_ids[d['id']], name={'en': d['name']}, faction='Adeptus Custodes',
                                        detachmentPoints=d['dp'], forceDispositions=[dict(name={'en': n}) for n in dispositions(d['fd'])]))
        cards = [dict(name={'en': d['rule']['n']}, rules=[dict(type='text', order=1, text={'en': d['rule']['t']})])]
        if d.get('ka'):
            cards.append(dict(name={'en': f'Favoured Ka’tah: {d["ka"]["n"]}'}, rules=[dict(type='text', order=1, text={'en': d['ka']['t']})]))
        data['rules']['detachment'].append(dict(detachment=d['name'], rules=cards))
        points['detachments'].append(dict(name=d['name'], dp=d['dp'], enhancements=[dict(
            name=e['name'] + (' (Upgrade)' if e['k'] == 'upg' else ''), points=e['p']) for e in SOURCE['ENH'] if e['det'] == d['id']]))
        for i, (name, cp, when, effect) in enumerate(d['strats']):
            if d['id'] == 'moritoi':
                when = {'Honoured Interred': 'Your Shooting phase or the Fight phase',
                        'Unstoppable Momentum': 'Your Movement phase or your Charge phase'}.get(name, when)
                if name == 'Honoured Interred':
                    effect = 'Your unit gains Honoured Interred (Aura): Friendly ADEPTUS CUSTODES units within 6" of this unit can re-roll hit rolls of 1.'
            if name == 'Superhuman Focus':
                when = 'End of any phase'
            unsupported = name in {'Superhuman Focus', 'Gilded Champion', 'In Auramite Clad', 'Vigil Unending', 'Honoured Interred'}
            phases = re.findall(r'Command|Movement|Shooting|Charge|Fight', when)
            data['stratagems'].append(dict(id=identity(f'{d["id"]}/strat/{i}'), name={'en': name}, cost=cp,
                detachment=d['name'], when={'en': when}, effect={'en': effect},
                phase=[p.lower() for p in phases] if phases else ['any'] if when == 'Any phase' else [],
                turn=None if unsupported else 'opponents' if re.search(r'\bopponent', when, re.I)
                     else 'your' if re.search(r'\byour\b', when, re.I) else 'either'))
    for e in SOURCE['ENH']:
        required = [k for k in e['req'] if k != 'CHARACTER']
        eligibility = ' '.join(required)
        if e.get('any'):
            eligibility += ' ' + '/'.join(e['any'])
        if e.get('not'):
            eligibility += ' (excluding ' + ' or '.join(e['not']) + ' models)'
        text = eligibility + (' unit only. ' if e['k'] == 'upg' else ' model only. ') + e['t']
        data['enhancements'].append(dict(id=enhancements[e['id']]['id'], name={'en': enhancements[e['id']]['name']},
            detachment=next(d['name'] for d in SOURCE['DETS'] if d['id'] == e['det']), cost=str(e['p']),
            description={'en': text}, keywords=[*e['req'], *e.get('any', [])],
            equipableByNonCharacter=e['k'] == 'upg'))
    save(ROOT / 'Imperium - Adeptus Custodes.json', {'catalogue': catalogue})
    save(ROOT / 'data/adeptus-custodes.yaml', points)
    save(ROOT / '11th/gdc/adeptuscustodes.json', data)


if __name__ == '__main__':
    build()

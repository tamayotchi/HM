"""Pure dashboard generation shared by local preflight and HA asset deployment."""
VIEW_PATHS = {1: 'first-floor', 2: 'second-floor', 3: 'third-floor', 4: 'fourth-floor'}


def build_dashboard(config, source_layout, image_url):
    views = []
    seen_entities = set()
    for floor in config['floors']:
        source = next(f for f in source_layout['floors'] if f['floor'] == floor['floor'])
        label_positions = {l['text']: l.get('screen_position', {}) for l in source['labels']}
        card = {
            'type': 'custom:house-floorplan-card',
            'title': floor['title'], 'subtitle': floor['subtitle'], 'note': floor['note'],
            'floor_label': f'Floor {floor["floor"]} / 4',
            'image': image_url(floor['image_file']),
            'labels': [{**{k: l[k] for k in ('text', 'x', 'y')},
                        **label_positions.get(l['text'], {})} for l in floor['labels']],
            'lights': [],
        }
        if source.get('model_only'):
            assert not floor['lights'] and not floor.get('openings'), 'Model-only floors cannot bind entities'
        for field in ('model_source', 'image_alt', 'model_only'):
            if field in source:
                card[field] = source[field]
        if floor.get('openings'):
            card['openings'] = [{k: o[k] for k in ('entity', 'name', 'kind', 'x', 'y')}
                                for o in floor['openings']]
        for light in floor['lights']:
            assert light['entity'].split('.')[0] in ('light', 'switch')
            assert light['entity'] not in seen_entities, 'Duplicate circuit binding'
            seen_entities.add(light['entity'])
            record = {k: light[k] for k in ('entity', 'name', 'room', 'x', 'y')}
            record['image'] = image_url(light['image_file'])
            if light.get('compact_hide'):
                record['compact_hide'] = True
            card['lights'].append(record)
        views.append({'title': floor['title'], 'path': VIEW_PATHS[floor['floor']],
                      'type': 'panel', 'cards': [card]})
    assert len(views) == len({v['path'] for v in views}), 'Duplicate view paths'
    views.append(build_overview_view(views))
    return {'title': 'House · 3D', 'background': '#080f1b', 'views': views}


def build_overview_view(views):
    """Reuse exact published floor assets/bindings; no new models or guessed entities."""
    import copy
    floors = []
    for path in VIEW_PATHS.values():
        view = next(v for v in views if v.get('path') == path)
        card = copy.deepcopy(view['cards'][0])
        assert card['type'] == 'custom:house-floorplan-card'
        card.pop('type')
        card['navigation_path'] = '/house-3d/' + path
        floors.append(card)
    return {'title': 'All floors', 'path': 'all-floors', 'icon': 'mdi:home-floor-3',
            'type': 'panel', 'cards': [{'type': 'custom:house-overview-card',
                                      'title': 'House · All floors', 'floors': floors}]}

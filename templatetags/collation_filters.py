from django import template


register = template.Library()


@register.filter(name='get_range')
def get_range(value):
    return range(value+1)[1:]


@register.filter(name='get_offset')
def get_offset(i, page_size):
    return (i-1)*page_size


@register.filter(name='get_row_class')
def get_row_class(value):
    if value % 2 == 1:
        return 'odd'
    return ''


@register.filter(name='get_mapping_field')
def get_mapping_field(form, ceremony):
    return form['mappings_%s' % ceremony].field.get_bound_field(form, 'mappings_%s' % ceremony)


@register.filter(name='get_ceremony_mapping')
def get_ceremony_mapping(data, ceremony):
    if data['details'] and ceremony in data['details'] and data['details'][ceremony] is not None:
        return data['details'][ceremony]
    else:
        return ''


@register.filter(name='get_overtext')
def get_overtext(overtext, app=None):
    if app:
        if int(app['start']) % 2 == 1:
            required_text = []
        else:
            real_start = int(app['start']/2)-1
            real_end = int(app['end']/2)-1
            required_text = overtext[0]['tokens'][real_start:real_end+1]
    else:
        required_text = overtext[0]['tokens']
    words = []
    for token in required_text:
        word = []
        if 'pc_before' in token:
            word.append(token['pc_before'])
        word.append(token['original'])
        if 'pc_after' in token:
            word.append(token['pc_after'])
        words.append(''.join(word))
    return ' '.join(words)


@register.filter(name='get_overtext_type')
def get_overtext_type(overtext, app=None):
    if int(app['start']) % 2 == 1:
        pass
    else:
        real_start = int(app['start']/2)-1
        real_end = int(app['end']/2)-1
        token = overtext[0]['tokens'][real_start]
        if 'type' in token:
            return token['type']
    return ''


@register.filter(name='get_overtext_language')
def get_overtext_language(overtext, app=None):

    if int(app['start']) % 2 == 1:
        pass
    else:
        real_start = int(app['start']/2)-1
        real_end = int(app['end']/2)-1
        token = overtext[0]['tokens'][real_start]
        if 'language' in token:
            return token['language']
    return None


@register.filter(name='has_ritual_direction_before')
def has_ritual_direction_before(overtext, app):
    if int(app['start']) % 2 == 0:
        real_start = int(app['start']/2)-1
        if 'rd_before' in overtext[0]['tokens'][real_start]:
            return True
    return False


@register.filter(name='has_no_linebreak_before_ritual_direction_before')
def has_no_linebreak_before_ritual_direction_before(overtext, app):
    if int(app['start']) % 2 == 0:
        real_start = int(app['start']/2)-1
        if 'no_linebreak_before_rd_before' in overtext[0]['tokens'][real_start]:
            return True
    return False


@register.filter(name='get_rd_before')
def get_rd_before(overtext, app):
    real_start = int(app['start']/2)-1
    if 'rd_before' in overtext[0]['tokens'][real_start]:
        return overtext[0]['tokens'][real_start]['rd_before']
    return ''


@register.filter(name='get_rdt_before')
def get_rdt_before(overtext, app):
    real_start = int(app['start']/2)-1
    if 'rdt_before' in overtext[0]['tokens'][real_start]:
        return overtext[0]['tokens'][real_start]['rdt_before']
    return 'No trancription provided'


@register.filter(name='has_ritual_direction_after')
def has_ritual_direction_after(overtext, app):
    if int(app['end']) % 2 == 0:
        real_end = int(app['end']/2)-1
        if 'rd_after' in overtext[0]['tokens'][real_end]:
            return True
    else:
        real_end = int(app['end']/2)-2
        if 'rd_after' in overtext[0]['tokens'][real_end]:
            return True
    return False


@register.filter(name='has_no_linebreak_before_ritual_direction_after')
def has_no_linebreak_before_ritual_direction_after(overtext, app):
    if int(app['start']) % 2 == 0:
        real_start = int(app['start']/2)-1
        if 'no_linebreak_before_rd_after' in overtext[0]['tokens'][real_start]:
            return True
    return False


@register.filter(name='get_rd_after')
def get_rd_after(overtext, app):
    real_end = int(app['end']/2)-1
    if 'rd_after' in overtext[0]['tokens'][real_end]:
        return overtext[0]['tokens'][real_end]['rd_after']
    return ''


@register.filter(name='get_rdt_after')
def get_rdt_after(overtext, app):
    real_end = int(app['end']/2)-1
    if 'rdt_after' in overtext[0]['tokens'][real_end]:
        return overtext[0]['tokens'][real_end]['rdt_after']
    return 'No trancription provided'


@register.filter(name='unescape')
def unescape(text):
    return text.replace('&lt;', '<').replace('&gt;', '>')

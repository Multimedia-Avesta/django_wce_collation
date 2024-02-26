# -*- coding: utf-8 -*-
import re
import codecs
import json
import string
from collections import OrderedDict
from io import StringIO
from lxml import etree
from collation.exceptions import DataStructureError, HandSortError, ReadingConstructionError
from collation.models import Project
from transcriptions import models


class YasnaExporter(object):

    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0', 'xml': 'http://www.w3.org/XML/1998/namespace'}
    alphabet_list = list(string.ascii_lowercase)

    def __init__(self, project_id=None, format='positive_xml', overlap_status_to_ignore=['deleted', 'overlapped'],
                 ignore_basetext=False, settings={}):

        if project_id is None:
            raise ValueError('__init__() must have a value the keyword argument \'project_id\'')
        self.project = Project.objects.get(id=project_id)

        self.format = format
        self.ignore_basetext = ignore_basetext
        self.overlap_status_to_ignore = overlap_status_to_ignore

        if 'main_language' in settings:
            self.main_language = settings['main_language']
        else:
            self.main_language = 'ae'

        if 'add_raised_plus' in settings and settings['add_raised_plus'] in [True, 'True', 'true']:
            self.add_raised_plus = True
        else:
            self.add_raised_plus = False

        if 'book_prefix' in settings:
            self.book_prefix = settings['book_prefix']
        else:
            self.book_prefix = ''

        self.settings = settings

        self.hand_order_lookup = None
        self.hand_list = None
        self.sigla_lookup = None

    def export_data(self, data):

        # sometimes the data doesn't seem to be correct so check for this first
        if 'structure' not in data[0]:
            raise DataStructureError('There was a problem accessing the data. Please try again.')

        self.sigla_lookup, self.hand_list = self.create_sigla_lookup_and_hand_list(data)
        self.hand_order_lookup = self.create_hand_order_lookup(self.sigla_lookup)
        data = self.merge_lac_readings(data)
        filtered_data = self.filter_hands(data)
        # fix the labels because anything that is after lac in the interface won't have one and they might have
        # been reordered
        filtered_data = self.fix_labels(filtered_data)
        # now always merge sigla and suffixes
        filtered_data = self.merge_sigla_and_suffixes(filtered_data)
        # filter any supplements and related transcriptions
        # this can safely go after suffix merging because MUYA don't use any sigla suffixes
        filtered_data = self.filter_supplements(filtered_data)
        xml = self.get_structured_xml(filtered_data)

        if self.format == 'positive_xml':
            xml = self.add_witness_group_markers(xml)
            if self.settings:
                xml = self.apply_settings(xml, self.settings)
                xml = self.apply_unit_numbers(xml)
                xml = self.fix_v_encoding(xml)
                return xml

            xml = self.apply_unit_numbers(xml)
            xml = self.fix_v_encoding(xml)
            return xml

        xml = self.apply_unit_numbers(xml)
        xml = self.fix_v_encoding(xml)
        return xml

    def strip_encoding_declaration(self, xml):
        xml = xml.replace('<?xml version=\'1.0\' encoding=\'utf-8\'?>', '')
        xml = xml.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        xml = xml.replace('<?xml version=\'1.0\' encoding=\'UTF-8\'?>', '')
        xml = xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        return xml

    def add_marker_after(self, rdg, witness, marker):
        for idno in rdg.findall('.//tei:idno', self.namespaces):
            if idno.text == witness:
                char_elem = etree.Element('c')
                char_elem.text = marker
                idno.addnext(char_elem)
        return

    def get_witness_list(self, rdg):
        witnesses = []
        for wit in rdg.xpath('./tei:wit/tei:idno', namespaces=self.namespaces):
            witnesses.append(wit.text)
        return witnesses

    def add_witness_group_markers(self, xml):

        parser = etree.XMLParser(resolve_entities=False)
        tree = etree.parse(StringIO(self.strip_encoding_declaration(xml)), parser)
        tree = etree.ElementTree(tree.getroot())

        for rdg in tree.findall('.//tei:rdg', self.namespaces):
            id_list = self.get_witness_list(rdg)
            if len(id_list) > 1:
                witness_groups, witness_subgroups = self.get_witness_groups(id_list)
                for i, key in enumerate(witness_groups):
                    if len(witness_groups) >= 2 and i <= len(witness_groups)-2:
                        self.add_marker_after(rdg, witness_groups[key][-1], ';')
                for key in witness_subgroups:
                    if len(witness_subgroups[key][0]) > 0 and len(witness_subgroups[key][1]) > 0:
                        self.add_marker_after(rdg, witness_subgroups[key][0][-1], ',')
        return etree.tostring(etree.ElementTree(tree.getroot()), encoding='utf-8', xml_declaration=True).decode()

    def get_witness_subgroups(self, witness_groups):
        # this one doesn't need to be an ordered dict because it is just about the winesses not the label
        classified_witness_subgroups = {}
        for key in witness_groups:
            if key in ['Y', 'PY', 'VS']:
                if key == 'Y':
                    split_point = 100
                elif key == 'PY':
                    split_point = 500
                elif key == 'VS':
                    split_point = 4200

                classified_witness_subgroups[key] = []
                sg_1 = []
                sg_2 = []
                for witness in witness_groups[key]:
                    match = re.match(r'(\d+)\D*', witness)
                    numerical_siglum = int(match.group(1))
                    if numerical_siglum < split_point:
                        sg_1.append(witness)
                    else:
                        sg_2.append(witness)
                classified_witness_subgroups[key].append(sg_1)
                classified_witness_subgroups[key].append(sg_2)
        return classified_witness_subgroups

    def get_witness_groups(self, witnesses):
        latex = []
        classified_witnesses = OrderedDict()
        for witness in witnesses:
            match = re.match(r'^(\d+)\D*', witness)
            numerical_siglum = int(match.group(1))
            if numerical_siglum < 300:
                try:
                    classified_witnesses['Y'].append(witness)
                except KeyError:
                    classified_witnesses['Y'] = [witness]
            elif numerical_siglum < 400:
                try:
                    classified_witnesses['YiR'].append(witness)
                except KeyError:
                    classified_witnesses['YiR'] = [witness]
            elif numerical_siglum < 650:
                try:
                    classified_witnesses['PY'].append(witness)
                except KeyError:
                    classified_witnesses['PY'] = [witness]
            elif numerical_siglum < 700:
                try:
                    classified_witnesses['SY'].append(witness)
                except KeyError:
                    classified_witnesses['SY'] = [witness]
            elif numerical_siglum >= 2000 and numerical_siglum < 2200:
                try:
                    classified_witnesses['VrS'].append(witness)
                except KeyError:
                    classified_witnesses['VrS'] = [witness]
            elif numerical_siglum >= 4000 and numerical_siglum < 4600:
                try:
                    classified_witnesses['VS'].append(witness)
                except KeyError:
                    classified_witnesses['VS'] = [witness]
            elif numerical_siglum >= 5000 and numerical_siglum < 5200:
                try:
                    classified_witnesses['VytS'].append(witness)
                except KeyError:
                    classified_witnesses['VytS'] = [witness]
            else:
                try:
                    classified_witnesses['problems'].append(witness)
                except KeyError:
                    classified_witnesses['problems'] = [witness]
        subgroups = self.get_witness_subgroups(classified_witnesses)

        return classified_witnesses, subgroups

    def apply_unit_numbers(self, xml):

        parser = etree.XMLParser(resolve_entities=False)
        tree = etree.parse(StringIO(self.strip_encoding_declaration(xml)), parser)
        tree = etree.ElementTree(tree.getroot())

        for stanza in tree.findall('.//tei:div[@type="stanza"]', self.namespaces):
            counter = 1
            for app in stanza.findall('.//tei:app[@type="main"]', self.namespaces):
                current_n = app.get('n')
                app.set('n', '{}-{}'.format(current_n, counter))
                counter += 1
        return etree.tostring(etree.ElementTree(tree.getroot()), encoding='utf-8', xml_declaration=True).decode()

    def fix_v_encoding(self, xml):
        # although these look the same the first 2 examples have a special
        # space character between them ord 8203 in python
        xml = xml.replace('x​ͮ', 'xᵛ').replace('ŋ​ͮ', 'ŋᵛ')
        xml = xml.replace('xͮ', 'xᵛ').replace('ŋͮ', 'ŋᵛ')
        return xml

    def apply_settings(self, xml, settings):

        parser = etree.XMLParser(resolve_entities=False)
        tree = etree.parse(StringIO(self.strip_encoding_declaration(xml)), parser)
        tree = etree.ElementTree(tree.getroot())

        for ab in tree.findall('.//tei:ab', self.namespaces):
            for app in ab.findall('.//tei:app', self.namespaces):
                unit_context = app.get('n')
                if app.get('type') == 'main':
                    if (settings['include_apparatus'] is False
                            or unit_context in settings['omit_apparatus']):
                        # delete the rdg tags
                        for rdg in app.findall('.//tei:rdg', self.namespaces):
                            app.remove(rdg)
                if app.get('type') == 'ritual_direction':
                    if 'ritual_directions' not in settings:
                        ab.remove(app)
                    elif settings['ritual_directions'] == 'transliteration':
                        for rd_transcription in app.findall('.//tei:lem[@type="transcription"]', self.namespaces):
                            app.remove(rd_transcription)

                    elif settings['ritual_directions'] == 'transcription':
                        for rd_transliteration in app.findall('.//tei:lem[@type="transliteration"]', self.namespaces):
                            app.remove(rd_transliteration)

        return etree.tostring(etree.ElementTree(tree.getroot()), encoding='utf-8', xml_declaration=True).decode()

    def get_structured_xml(self, data, negative_apparatus=False,
                           consolidate_om_verse=False, consolidate_lac_verse=False,
                           include_lemma_when_no_variants=False):
        apptree = etree.fromstring('<TEI><text><body></body></text></TEI>')

        header_string = '''<teiHeader><fileDesc><titleStmt><title type="document">An apparatus of the Yasna</title>
                        </titleStmt>
                        <publicationStmt><distributor>
                        <name type="org">Corpus Avesticum (CoAv): The Multimedia Yasna (MUYA)</name>
                        <name type="org">School of Oriental and African Studies (SOAS)</name>
                        <name type="org">University of London (UoL)</name>
                        </distributor>
                        <availability><p>Attribution 4.0 International (CC BY 4.0) Available for re-use under a
                        creative commons license provided attribution is made to the original creators</p>
                        </availability></publicationStmt><sourceDesc>
                        <p>A TEI encoding of the apparatus of a section of the Yasna.</p>
                        </sourceDesc></fileDesc>
                        <encodingDesc><projectDesc><p>This apparatus was made by the Multimedia Yasna Project.</p>
                        </projectDesc></encodingDesc></teiHeader>'''
        header_tei = etree.fromstring(header_string)
        apptree.insert(0, header_tei)

        for entry in data:
            context = entry['context']
            book_n, chapter_n, stanza_n, line_n = context.split('.')

            book_n = '{}{}'.format(self.book_prefix, book_n)

            # this is ab element
            vtree = self.get_unit_xml(entry, negative_apparatus,
                                      consolidate_om_verse=consolidate_om_verse,
                                      consolidate_lac_verse=consolidate_lac_verse,
                                      include_lemma_when_no_variants=include_lemma_when_no_variants)

            if len(apptree.findall('.//div[@type="stanza"][@xml:id="{0}.{1}.{2}-APP"]'.format(book_n,
                                                                                              chapter_n,
                                                                                              stanza_n),
                                   self.namespaces)) > 0:
                apptree.findall('.//div[@type="stanza"][@xml:id="{0}.{1}.{2}-APP"]'.format(book_n,
                                                                                           chapter_n,
                                                                                           stanza_n),
                                self.namespaces)[0].append(vtree)

            elif len(apptree.findall('.//div[@type="chapter"][@xml:id="{0}.{1}-APP"]'.format(book_n, chapter_n),
                                     self.namespaces)) > 0:
                # make the stanza
                stanza = etree.Element('div')
                stanza.set('type', 'stanza')
                stanza.set('{http://www.w3.org/XML/1998/namespace}id', '{0}.{1}.{2}-APP'.format(book_n,
                                                                                                chapter_n,
                                                                                                stanza_n))
                stanza.append(vtree)
                apptree.findall('.//div[@type="chapter"][@xml:id="{0}.{1}-APP"]'.format(book_n, chapter_n),
                                self.namespaces)[0].append(stanza)

            elif len(apptree.findall('.//div[@type="book"][@xml:id="{0}-APP"]'.format(book_n), self.namespaces)) > 0:
                # make the chapter and stanza
                chap = etree.Element('div')
                chap.set('type', 'chapter')
                chap.set('{http://www.w3.org/XML/1998/namespace}id', '{0}.{1}-APP'.format(book_n, chapter_n))
                stanza = etree.Element('div')
                stanza.set('type', 'stanza')
                stanza.set('{http://www.w3.org/XML/1998/namespace}id', '{0}.{1}.{2}-APP'.format(book_n,
                                                                                                chapter_n,
                                                                                                stanza_n))
                stanza.append(vtree)
                chap.append(stanza)
                apptree.findall('.//div[@type="book"][@xml:id="{0}-APP"]'.format(book_n),
                                self.namespaces)[0].append(chap)

            else:
                # make the book, chapter and stanza
                bk = etree.Element('div')
                bk.set('type', 'book')
                bk.set('{http://www.w3.org/XML/1998/namespace}id', '{0}-APP'.format(book_n))
                chap = etree.Element('div')
                chap.set('type', 'chapter')
                chap.set('{http://www.w3.org/XML/1998/namespace}id', '{0}.{1}-APP'.format(book_n, chapter_n))
                stanza = etree.Element('div')
                stanza.set('type', 'stanza')
                stanza.set('{http://www.w3.org/XML/1998/namespace}id', '{0}.{1}.{2}-APP'.format(book_n,
                                                                                                chapter_n,
                                                                                                stanza_n))
                stanza.append(vtree)
                chap.append(stanza)
                bk.append(chap)
                body = apptree.findall('.//body', self.namespaces)[0]
                body.append(bk)

        stringified_xml = etree.tostring(apptree, encoding='utf-8').decode()
        xml_base = stringified_xml.replace('<TEI>',
                                           '<?xml version="1.0" encoding="utf-8"?>'
                                           '<?xml-stylesheet type="text/xsl" href="../muya_apparatus.xsl"?>'
                                           '{}<TEI xmlns="http://www.tei-c.org/ns/1.0">'.format(self.get_doctype()))

        return xml_base

    def get_doctype(self):
        doctype = ('<!DOCTYPE TEI [ '
                   '<!ENTITY lac "<abbr type=\'reading\'>lac.</abbr>"> '
                   '<!ENTITY om "<abbr type=\'reading\'>om.</abbr>"> '
                   '<!ENTITY abbr "<abbr type=\'reading\'>abbr.</abbr>"> '
                   '<!ENTITY suppliedabbr "<abbr type=\'reading\'>supplied abbr.</abbr>"> '
                   '<!ENTITY notexp "<abbr type=\'reading\'>not exp.</abbr>"> '
                   '<!ENTITY nonleg "<abbr type=\'reading\'>non leg.</abbr>"> '
                   ']>')
        return doctype

    def get_unit_xml(self, entry, negative_apparatus=False,
                     consolidate_om_verse=True, consolidate_lac_verse=True,
                     include_lemma_when_no_variants=False):

        context = '{}{}'.format(self.book_prefix, entry['context'])
        basetext_siglum = entry['structure']['overtext'][0]['id']

        apparatus = entry['structure']['apparatus'][:]

        # make sure we append lines in order
        ordered_keys = []
        for key in entry['structure']:
            if re.match(r'apparatus\d+', key) is not None:
                ordered_keys.append(int(key.replace('apparatus', '')))
        ordered_keys.sort()

        for num in ordered_keys:
            apparatus.extend(entry['structure']['apparatus{}'.format(num)])

        vtree = etree.fromstring('<ab xml:id="{}-APP"></ab>'.format(context))
        # here deal with the whole verse lac and om and only use witnesses elsewhere not in these lists
        missing = []
        if consolidate_om_verse or consolidate_lac_verse:
            app = etree.fromstring('<app type="lac" n="{}"><lem wit="editorial">Whole verse</lem></app>'.format(context))

            if consolidate_lac_verse:
                if len(entry['structure']['lac_readings']) > 0:
                    rdg = etree.Element('rdg')

                    rdg.set('type', 'lac')
                    rdg.text = 'Def.'
                    lac_witnesses = entry['structure']['lac_readings']
                    rdg.set('wit', ' '.join(lac_witnesses))
                    wit = etree.Element('wit')
                    for witness in lac_witnesses:
                        idno = etree.Element('idno')
                        idno.text = witness
                        wit.append(idno)
                    rdg.append(wit)
                    app.append(rdg)
                missing.extend(entry['structure']['lac_readings'])

            if consolidate_om_verse:
                if len(entry['structure']['om_readings']) > 0:
                    rdg = etree.Element('rdg')
                    rdg.set('type', 'lac')
                    rdg.text = 'Om.'
                    om_witnesses = entry['structure']['om_readings']
                    rdg.set('wit', ' '.join(om_witnesses))
                    wit = etree.Element('wit')
                    for witness in om_witnesses:
                        idno = etree.Element('idno')
                        idno.text = witness
                        wit.append(idno)
                    rdg.append(wit)
                    app.append(rdg)
                missing.extend(entry['structure']['om_readings'])

            vtree.append(app)

        # if we are ignoring the basetext add it to our missing list so it isn't listed (except n lemma)
        if self.ignore_basetext:
            missing.append(basetext_siglum)
        # this sort will change the order of the overlap units so longest starting at each index point comes first
        apparatus = sorted(apparatus, key=lambda d: (d['start'], -d['end']))
        optns = {'include_lemma_when_no_variants': include_lemma_when_no_variants,
                 'negative_apparatus': negative_apparatus
                 }
        app_units = self.get_app_units(apparatus, entry['structure']['overtext'][0], context, missing, optns)
        for app in app_units:
            vtree.append(app)

        return vtree

    def get_rd_app(self, context, token, position, index):
        app = etree.fromstring('<app type="ritual_direction" n="{}" loc="{}-{}"></app>'.format(context,
                                                                                               position,
                                                                                               index))
        lem = etree.Element('lem')
        lem.set('type', 'transliteration')
        if position == 'before':
            lem.text = token['rd_before']
            if 'no_linebreak_before_rd_before' in token and token['no_linebreak_before_rd_before'] is True:
                app.set('rend', 'no_linebreak')
        elif position == 'after':
            lem.text = token['rd_after']
            if 'no_linebreak_before_rd_after' in token and token['no_linebreak_before_rd_after'] is True:
                app.set('rend', 'no_linebreak')
        app.append(lem)
        lem = etree.Element('lem')
        lem.set('type', 'transcription')
        if position == 'before':
            try:
                lem.text = token['rdt_before']
            except KeyError:
                lem.text = 'transcription of ritual direction missing'
        elif position == 'after':
            try:
                lem.text = token['rdt_after']
            except KeyError:
                lem.text = 'transcription of ritual direction missing'
        app.append(lem)
        return app

    def hand_sort(self, x):
        if x == 'basetext':
            return 1000000000000, 0, 0
        m = re.match(r'^(\d+)(S?\d?)(-\d)?(\S*?)(\s.+)?$', x)
        sigla = int(m.group(1))
        if m.group(2) == '':
            supp = 0
        else:
            supp = 1
        if m.group(4) == '':
            hand = 0
        else:
            try:
                hand = self.hand_order_lookup['{}{}'.format(sigla, m.group(2))].index(m.group(4))
            except KeyError:
                raise HandSortError('Error while trying to sort the hands based on list in hand_order_lookup. '
                                    'Problem hand is {}. [Err: Yasna Exporter 472]'.format(x))
        return sigla, supp, hand

    def get_first_witness(self, rdg):
        if 'subreadings' in rdg.keys():
            try:
                witnesses = [rdg['witnesses'][0]]
            except IndexError:
                witnesses = []
            for type in rdg['subreadings']:
                for srdg in rdg['subreadings'][type]:
                    witnesses.append(srdg['witnesses'][0])
            witnesses.sort(key=self.hand_sort)
            return witnesses[0]
        return rdg['witnesses'][0]

    def reading_sort(self, x):
        try:
            rdg_type = x['type']
        except KeyError:
            rdg_type = None
            rdg_details = None
        else:
            try:
                rdg_details = x['details']
            except KeyError:
                rdg_details = None
        if rdg_type is None:
            type = 0
        else:
            if rdg_details in ['om.', 'om']:
                type = 1
            elif rdg_details in ['non leg.']:
                type = 2
            elif rdg_details in ['lac.']:
                type = 3
            elif rdg_details in ['abbr.', 'abbreviated text']:
                type = 4
            elif rdg_details in ['supplied abbr.', 'supplied abbreviated text']:
                type = 5
            elif rdg_details in ['not exp.']:
                type = 6
            else:
                type = 7
        first_witness = self.get_first_witness(x)
        if first_witness == 'basetext':
            return type, 100000000000, 0, 0
        m = re.match(r'^(\d+)(S?\d?)(-\d)?(\S*?)(\s.+)?$', first_witness)
        sigla = int(m.group(1))
        if m.group(2) == '':
            supp = 0
        else:
            supp = 1
        if m.group(4) == '':
            hand = 0
        else:
            hand = self.hand_order_lookup['{}{}'.format(sigla, m.group(2))].index(m.group(4))

        return type, sigla, supp, hand

    def put_lemma_reading_first(self, readings, text):
        match = None
        for i, reading in enumerate(readings):
            if 'text_string' in reading:
                if text[0] == reading['text_string']:
                    match = i
                elif r'\foreign' in text[0]:
                    m = re.match(r'^\\foreign\[[^\]]+?\]\{([^\}]+?)\}$', text[0])
                    if m and m.group(1) == reading['text_string']:
                        match = i
        if match is None or match == 0:
            return readings
        lemma_reading = readings.pop(match)
        readings.insert(0, lemma_reading)
        # now fix the labels again!
        for i, reading in enumerate(readings):
            if 'type' not in reading or reading['type'] == 'om':
                reading['label'] = self.alphabet_list[i]
        return readings

    def get_lemma_text(self, overtext, start, end):
        if start == end and start % 2 == 1:
            return ['', 'om']
        real_start = int(start/2)-1
        real_end = int(end/2)-1
        if 'type' in overtext['tokens'][real_start]:
            type = overtext['tokens'][real_start]['type']
        else:
            type = None
        word_list = [x['original'] for x in overtext['tokens']]
        if type is not None:
            return [' '.join(word_list[real_start:real_end+1]), type]
        return [' '.join(word_list[real_start:real_end+1])]

    def make_reading(self, reading, i, label, witnesses, type=None, subtype=None):
        rdg = etree.Element('rdg')
        rdg.set('n', label)
        text = self.get_text(reading, type)
        if type:
            rdg.set('type', type)
            if subtype:
                rdg.set('cause', subtype)
        elif len(text) > 1:
            rdg.set('type', text[1])
        split_text = re.split('(&[^&]+?;|<foreign[^/]+?</foreign>)', text[0])
        entity = None
        foreign = None
        for j, entry in enumerate(split_text):
            if entry.find('&') == 0:
                entity = etree.Entity(entry.replace('&', '').replace(';', ''))
                rdg.append(entity)
                foreign = None
            elif entry.find('<foreign') == 0:
                foreign = etree.Element('foreign')
                m = re.match('<foreign(?: xml:lang=")?([^"]*)?"?>([^<]+)</foreign>', entry)
                if m.group(1) != '':
                    foreign.set('{http://www.w3.org/XML/1998/namespace}lang', m.group(1))
                if j == 0 and len(witnesses) == 0 and self.add_raised_plus is True:
                    foreign.text = '⁺{}'.format(m.group(2))
                else:
                    foreign.text = m.group(2)
                rdg.append(foreign)
                entity = None
            elif entry != '':
                if j == 0 and len(witnesses) == 0 and self.add_raised_plus is True:
                    entry = '⁺{}'.format(entry)
                if entity is None and foreign is None:
                    rdg.text = entry
                elif entity is not None:
                    entity.tail = entry
                elif foreign is not None:
                    foreign.tail = entry
                else:
                    raise ReadingConstructionError('There was a problem adding the text to the reading'
                                                   '[err: yasnaExporter 602]')
        pos = i+1
        rdg.set('varSeq', str(pos))
        if len(witnesses) > 0:
            rdg.set('wit', ' '.join(witnesses))
            wit = etree.Element('wit')
            for witness in witnesses:
                idno = etree.Element('idno')
                idno.text = witness
                wit.append(idno)
            rdg.append(wit)

        return rdg

    def get_app_units(self, apparatus, overtext, context, missing, optns):
        app_list = []
        for unit in apparatus:
            start = unit['start']
            end = unit['end']
            real_start = int(start/2)-1
            real_end = int(end/2)-1
            if 'rd_before' in overtext['tokens'][real_start]:
                app_list.append(self.get_rd_app(context, overtext['tokens'][real_start], 'before', start))

            app = etree.fromstring('<app type="main" n="{}" from="{}" to="{}"></app>'.format(context, start, end))
            lem = etree.Element('lem')
            lem.set('wit', overtext['id'])
            text = self.get_lemma_text(overtext, int(start), int(end))
            corrected_text = text[0].replace('P+.', ' ')  # replace for collations against older basetexts
            lem.text = corrected_text.strip()
            if len(text) > 1:
                lem.set('type', text[1])
            app.append(lem)
            readings = False
            if optns['include_lemma_when_no_variants']:
                readings = True

            # An extra sort to put the main reading that matches the lemma first
            unit['readings'] = self.put_lemma_reading_first(unit['readings'], text)
            for i, reading in enumerate(unit['readings']):
                wits = self.get_witnesses(reading, missing)
                if optns['negative_apparatus'] is True:
                    if ((len(wits) > 0 or reading['label'] == 'a')
                            and ('overlap_status' not in reading
                                 or reading['overlap_status'] not in self.overlap_status_to_ignore)):
                        if reading['label'] == 'a':
                            wits = []
                        if len(wits) > 0:
                            readings = True
                        if 'label' in reading:
                            label = reading['label']
                        else:
                            label = ''
                        app.append(self.make_reading(reading, i, label, wits))
                    if 'subreadings' in reading:
                        for key in self.order_subreading_classes(list(reading['subreadings'])):
                            for subreading in reading['subreadings'][key]:
                                wits = self.get_witnesses(subreading, missing)
                                if len(wits) > 0:
                                    readings = True
                                    if 'label' in reading:
                                        label = reading['label']
                                    else:
                                        label = ''
                                    app.append(self.make_reading(subreading, i, '{}{}'.format(label,
                                                                                              subreading['suffix']),
                                                                 wits, 'subreading', key))

                else:
                    if ('overlap_status' not in reading
                            or reading['overlap_status'] not in self.overlap_status_to_ignore):

                        if len(wits) > 0 or (len(wits) == 0 and 'subreadings' in reading) or i == 0:
                            readings = True
                            if 'label' in reading:
                                label = reading['label']
                            else:
                                label = ''
                            app.append(self.make_reading(reading, i, label, wits))

                    if 'subreadings' in reading:
                        for key in self.order_subreading_classes(list(reading['subreadings'])):
                            for subreading in reading['subreadings'][key]:
                                wits = self.get_witnesses(subreading, missing)
                                if len(wits) > 0:
                                    readings = True
                                    if 'label' in reading:
                                        label = reading['label']
                                    else:
                                        label = ''
                                    app.append(self.make_reading(subreading, i, '{}{}'.format(label,
                                                                                              subreading['suffix']),
                                                                 wits, 'subreading', key))
            if readings:
                app_list.append(app)
            if 'linebreak_after' in unit and unit['linebreak_after'] is True:
                linebreak = lem = etree.Element('lb')
                app_list.append(linebreak)
            if 'rd_after' in overtext['tokens'][real_end]:
                app_list.append(self.get_rd_app(context, overtext['tokens'][real_end], 'after', end))
        return app_list

    def class_sort(self, x):
        if x == 'abbreviation':
            return 99
        if x == 'reconstructed' or x == 'abbreviation|reconstructed':
            return 90
        value = 0
        if 'phonetic' in x:
            value += 20
        if 'orthographic' in x:
            value += 40
            if 'phonetic' in x:
                value -= 30
        if 'reconstructed' in x:
            value += 5
        return value

    def order_subreading_classes(self, subreading_classes):
        subreading_classes.sort(key=self.class_sort)
        return subreading_classes

    def create_hand_order_lookup(self, data):
        hand_order_lookup = {}
        for entry in data:
            hand_order_lookup[data[entry]['base_siglum']] = data[entry]['hands']
        return hand_order_lookup

    def create_sigla_lookup_and_hand_list(self, data):
        transcription_list = []
        sigla_lookup = {}
        hand_list = {}

        for tid in data[0]['structure']['hand_id_map']:
            if data[0]['structure']['hand_id_map'][tid] not in transcription_list:
                transcription_list.append(data[0]['structure']['hand_id_map'][tid])

        # get the necessary transcription and collation unit data
        # (transcription for ordered hands list)
        # (verses for all of the collation units that have multiple hands expected)
        transcriptions = models.Transcription.objects.filter(identifier__in=transcription_list)

        ceremony_mappings = {}
        if self.project.configuration is not None and 'ceremony_mapping' in self.project.configuration:
            for context in self.project.configuration['ceremony_mapping'].keys():
                if context in [x['context'] for x in data]:
                    ceremony_mappings[context] = self.project.configuration['ceremony_mapping'][context]

        full_contexts = [x['context'] for x in data]
        mapped_contexts = {}
        for c in full_contexts:
            mapped_contexts[c] = c
        for context in ceremony_mappings.keys():
            if context not in full_contexts:
                full_contexts.append(context)
            for ceremony in ceremony_mappings[context]['details'].keys():
                if (ceremony_mappings[context]['details'][ceremony] is not None
                        and ceremony_mappings[context]['details'][ceremony] != ''):
                    maps = ceremony_mappings[context]['details'][ceremony].split(';')
                    for map in maps:
                        if map not in full_contexts:
                            full_contexts.append(map)
                        if map not in mapped_contexts:
                            mapped_contexts[map] = context

        collation_units = models.CollationUnit.objects.filter(transcription__identifier__in=transcription_list,
                                                              context__in=full_contexts).distinct()

        for transcript in transcriptions:
            sigla_lookup[transcript.identifier] = {'base_siglum': transcript.siglum}
            if transcript.corrector_order is not None:
                sigla_lookup[transcript.identifier]['hands'] = transcript.corrector_order
            else:
                sigla_lookup[transcript.identifier]['hands'] = []

        for unit in collation_units:
            if unit.witnesses and len(unit.witnesses) > 1:
                if mapped_contexts[unit.context] not in hand_list:
                    hand_list[mapped_contexts[unit.context]] = {}
                if unit.siglum not in hand_list[mapped_contexts[unit.context]]:
                    hand_list[mapped_contexts[unit.context]][unit.siglum] = {}
                hand_list[mapped_contexts[unit.context]][unit.siglum]['hands'] = [x['id'] for x in unit.witnesses]
                hand_list[mapped_contexts[unit.context]][unit.siglum]['transcription_identifier'] = unit.transcription_identifier

        sigla_lookup = self.expand_sigla_lookup(sigla_lookup)
        return sigla_lookup, hand_list

    def filter_hands(self, data):
        for entry in data:
            context = entry['context']
            if context in self.hand_list:
                for key in entry['structure']:
                    if key.find('apparatus') != -1:
                        for i, unit in enumerate(entry['structure'][key]):
                            for siglum in self.hand_list[context]:
                                hands = self.hand_list[context][siglum]['hands']
                                chron_hands = self.sigla_lookup[self.hand_list[context][siglum]['transcription_identifier']]['hands']
                                ordered_expected_hands = self.order_expected_hands(hands, siglum, chron_hands)
                                for reading in unit['readings']:
                                    self.fix_reading_hands(reading, siglum, ordered_expected_hands, context)
                                    if 'subreadings' in reading:
                                        for type in reading['subreadings']:
                                            for subreading in reading['subreadings'][type]:
                                                self.fix_reading_hands(subreading, siglum,
                                                                       ordered_expected_hands, context)
                                        reading['subreadings'] = self.merge_subreading_types(reading['subreadings'])
                            unit['readings'].sort(key=self.reading_sort)
            else:
                for key in entry['structure']:
                    if key.find('apparatus') != -1:
                        for unit in entry['structure'][key]:
                            unit['readings'].sort(key=self.reading_sort)

        return data

    def fix_labels(self, data):
        for entry in data:
            for key in entry['structure']:
                if key.find('apparatus') != -1:
                    for unit in entry['structure'][key]:
                        for i, reading in enumerate(unit['readings']):
                            if 'type' not in reading or reading['type'] == 'om':
                                reading['label'] = self.alphabet_list[i]
        return data

    def reorganise_supplement_settings(self, settings):
        organised_settings = {}
        for siglum in settings:
            m = re.match(r'^(\d+)(S\d?)$', siglum)
            base_ms = m.group(1)
            supplement_type = m.group(2)
            if base_ms in organised_settings:
                if siglum not in organised_settings[base_ms]:
                    organised_settings[base_ms].append(siglum)
            else:
                organised_settings[base_ms] = [siglum]
        return organised_settings

    def filter_supplements(self, data):
        for entry in data:
            if self.project.supplement_range is None:
                return data
            context = entry['context']
            witnesses_to_delete = []
            for siglum in self.project.supplement_range:
                m = re.match(r'^(\d+)(S\d?)$', siglum)
                base_ms = m.group(1)
                supplement_type = m.group(2)
                if context in self.project.supplement_range[siglum]:
                    if base_ms not in witnesses_to_delete:
                        witnesses_to_delete.append(base_ms)
                else:
                    if siglum not in witnesses_to_delete:
                        witnesses_to_delete.append(siglum)

            for key in entry['structure']:
                if key.find('apparatus') != -1:
                    for unit in entry['structure'][key]:
                        for reading in unit['readings']:
                            # only delete witness if the reading has no text
                            if len(reading['text']) == 0:
                                for witness in witnesses_to_delete:
                                    try:
                                        reading['witnesses'].remove(witness)
                                    except ValueError:
                                        pass
                            if 'subreadings' in reading:
                                for type in reading['subreadings']:
                                    for subreading in reading['subreadings'][type]:
                                        if len(subreading['text']) == 0:
                                            for witness in witnesses_to_delete:
                                                try:
                                                    subreading['witnesses'].remove(witness)
                                                except ValueError:
                                                    pass
        return data

    def merge_lac_readings(self, data):
        for entry in data:
            for key in entry['structure']:
                if key.find('apparatus') != -1:
                    for i, unit in enumerate(entry['structure'][key]):
                        rdgs = {}
                        for j, reading in enumerate(unit['readings']):
                            if 'type' in reading.keys() and reading['type'] in ['om_verse', 'om', 'lac_verse', 'lac']:
                                if 'details' in reading.keys():
                                    if reading['details'] == 'not expected':
                                        text = 'not exp.'
                                    elif reading['details'].find('gap') == 0 or reading['details'].find('ill') == 0:
                                        text = 'non leg.'
                                    elif reading['details'].find('lac') == 0:
                                        text = 'lac.'
                                    else:
                                        text = reading['details']
                                else:
                                    text = reading['type']
                                if text not in rdgs:
                                    reading['details'] = text
                                    rdgs[text] = reading
                                else:
                                    wit_suf_dict = {}
                                    rdgs[text]['witnesses'].extend(reading['witnesses'])
                                    rdgs[text]['suffixes'].extend(reading['suffixes'])
                                    # link witnesses and suffixes in dict
                                    for k, wit in enumerate(rdgs[text]['witnesses']):
                                        wit_suf_dict[wit] = rdgs[text]['suffixes'][k]
                                    # sort list of witnesses
                                    rdgs[text]['witnesses'].sort(key=self.hand_sort)
                                    # put the data form dict back in the order of the new list
                                    ordered_suf = []
                                    for wit in rdgs[text]['witnesses']:
                                        ordered_suf.append(wit_suf_dict[wit])
                                    rdgs[text]['suffixes'] = ordered_suf
                                    unit['readings'][j] = None

                        unit['readings'] = [x for x in unit['readings'] if x is not None]

        return data

    def merge_subreading_types(self, subreadings):
        new_subreadings = {}
        for type in subreadings:
            type_set = set(type.replace('_', '|').split('|'))
            type_list = list(type_set)
            type_list.sort()
            new_type = '|'.join(type_list)
            if new_type in new_subreadings.keys():
                new_subreadings[new_type].extend(subreadings[type])
            else:
                new_subreadings[new_type] = subreadings[type]
        for type in new_subreadings:
            new_subreadings[type].sort(key=self.reading_sort)
        return new_subreadings

    def get_hand_abbr(self, hand_string):
        if hand_string == 'firsthand':
            return 'C*'
        if hand_string.find('corrector') != -1:
            return hand_string.replace('corrector', 'C')
        if hand_string == 'glossator':
            return 'G'
        return hand_string

    def expand_sigla_lookup(self, sigla_lookup):
        for key in sigla_lookup:
            sigla_lookup[key]['hands'] = [self.get_hand_abbr(h) for h in sigla_lookup[key]['hands']]
            if len(sigla_lookup[key]['hands']) > 0:
                sigla_lookup[key]['hands'].insert(0, '*')
            sigla_lookup[key]['hands'].append('A*')
            sigla_lookup[key]['hands'].append('AC')
        return sigla_lookup

    # take all the hands we are expecting for this MS in this verse and order them
    # chronologically using the list from the transcription header
    def order_expected_hands(self, hand_list, siglum, chron_hands):
        new_hand_list = []
        for hand in chron_hands:
            if '{}{}'.format(siglum, hand) in hand_list:
                new_hand_list.append('{}{}'.format(siglum, hand))
        # this makes sure and Alt hands are added at the end -
        # these are out of the chronological flow and always appear in units where a MS is split between readings
        for hand in hand_list:
            if hand not in new_hand_list:
                new_hand_list.append(hand)
        return new_hand_list

    def fix_reading_hands(self, reading, siglum, ordered_expected_hands, context='unknown'):
        hands_for_deletion = []
        if 'suffixes' not in reading:
            raise DataStructureError('There is a problem with the structure of a unit (context is {}). First try '
                                     'reapproving the unit. If the problem persists please recollate the unit from '
                                     'the collation home page.'.format(context))
        if (self.all_hands_present(ordered_expected_hands, reading['witnesses'])
                and self.all_share_suffix(ordered_expected_hands, reading['witnesses'], reading['suffixes'])):
            # then we need to remove all the hands and replace with the siglum + suffix
            # find the lowest index, remove the hands and then at the lowest index add the siglum
            # delete from siglum at the same time to keep in line
            index = self.get_lowest_index_of_hand(ordered_expected_hands, reading['witnesses'])
            new_hand = siglum
            new_suffix = reading['suffixes'][index]
            for hand in ordered_expected_hands:
                reading['suffixes'].pop(reading['witnesses'].index(hand))
                reading['witnesses'].remove(hand)
            reading['witnesses'].insert(index, new_hand)
            reading['suffixes'].insert(index, new_suffix)
        else:
            delete = False
            for i, hand in enumerate(ordered_expected_hands):
                if hand in reading['witnesses']:
                    if delete is True:
                        # then this is a deletion candidate
                        if (reading['suffixes'][reading['witnesses'].index(hand)]
                                == reading['suffixes'][reading['witnesses'].index(ordered_expected_hands[i-1])]):
                            hands_for_deletion.append(hand)
                        else:
                            pass
                    else:
                        delete = True
                else:
                    delete = False
            if len(hands_for_deletion) > 0:
                pass
            for hand in hands_for_deletion:
                reading['suffixes'].pop(reading['witnesses'].index(hand))
                reading['witnesses'].remove(hand)

    def all_hands_present(self, hand_list, reading_witnesses):
        for hand in hand_list:
            if hand not in reading_witnesses:
                return False
        return True

    def all_share_suffix(self, hand_list, reading_witnesses, reading_suffixes):
        suffix = None
        for hand in hand_list:
            if suffix is None:
                suffix = reading_suffixes[reading_witnesses.index(hand)]
            if reading_suffixes[reading_witnesses.index(hand)] != suffix:
                return False

        return True

    def get_lowest_index_of_hand(self, hand_list, reading_witnesses):
        index = len(reading_witnesses) + 2
        for hand in hand_list:
            position = reading_witnesses.index(hand)
            if position < index:
                index = position
        return index

    def merge_sigla_and_suffixes(self, data):
        for entry in data:
            # here you need to merge sigla and suffixes for every reading in every
            # unit of every app line and delete the suffix list from each
            for key in entry['structure']:
                if key.find('apparatus') != -1:
                    for unit in entry['structure'][key]:
                        for reading in unit['readings']:
                            reading['witnesses'] = ['{}{}'.format(x, reading['suffixes'][i])
                                                    for i, x in enumerate(reading['witnesses'])]
                            del reading['suffixes']
                            if 'subreadings' in reading:
                                for type in reading['subreadings']:
                                    for subreading in reading['subreadings'][type]:
                                        subreading['witnesses'] = ['{}{}'.format(x, subreading['suffixes'][i])
                                                                   for i, x in enumerate(subreading['witnesses'])]
                                        del subreading['suffixes']

        return data

    def get_witnesses(self, reading, missing):
        witnesses = reading['witnesses']
        for miss in missing:
            if miss in witnesses:
                witnesses.remove(miss)
        for i, witness in enumerate(witnesses):
            if witness.find('secundamanu') != -1:
                witnesses[i] = witness.replace('secundamanu', 'sec.m.')
        return witnesses

    def add_xml_entities(self, text):
        text = text.replace('&lt;supplied abbreviated text&gt;', '&suppliedabbr;')
        text = text.replace('supplied abbr.', '&suppliedabbr;')

        text = text.replace('&lt;abbreviated text&gt;', '&abbr;')
        text = text.replace('abbr.', '&abbr;')

        pattern = re.compile(r'&lt;ill\s?[^&]*?&gt;')
        text = pattern.sub(r'&nonleg;', text)
        pattern = re.compile(r'&lt;gap\s?[^&]*?&gt;')
        text = pattern.sub('&nonleg;', text)
        pattern = re.compile(r'&lt;lac\s?[^&]*?&gt;')
        text = pattern.sub('&lac;', text)

        return text

    def get_text_from_text_string(self, reading):
        text = reading['text_string']
        text = self.add_xml_entities(text)

        reading_tokens = text.split(' ')

        reading_text = []
        original_tokens = self.get_representative_witness_token_list(reading)
        if len(original_tokens) == len(reading_tokens):
            # then we add foreign tags by word
            for i, token in enumerate(original_tokens):
                if 'foreign' in token and token['foreign'] is True:
                    language = token['language'] if 'language' in token else ''
                    reading_text.append('<foreign xml:lang="{}">{}</foreign>'.format(language,
                                                                                     reading_tokens[i]))
                else:
                    reading_text.append(reading_tokens[i])
        else:
            add_foreign_tags = True
            add_language = True
            other_language = None
            if len(original_tokens) == 0:
                add_foreign_tags = False
                add_language = False
            else:
                for token in original_tokens:
                    if 'foreign' not in token or token['foreign'] is False:
                        add_foreign_tags = False
                    else:
                        if other_language is None:
                            other_language = token['language']
                        elif other_language != token['language']:
                            add_language = False
            for token in reading_tokens:
                if add_foreign_tags is False:
                    reading_text.append(token)
                elif add_language is False:
                    reading_text.append('<foreign>{}</foreign>'.format(token))
                else:
                    reading_text.append('<foreign xml:lang="{}">{}</foreign>'.format(other_language, token))
        return [' '.join(reading_text)]

    def get_representative_witness_token_list(self, reading, suffix=None):
        target_witness = None
        if len(reading['witnesses']) == 1:
            target_witness = reading['witnesses'][0]
        else:
            for witness in reading['witnesses']:
                if 'standoff_subreadings' not in witness or witness not in reading['standoff_subreadings']:
                    target_witness = witness
                    break
        if suffix is not None:
            target_witness = '{}{}'.format(target_witness, suffix)
        if 'SR_text' in reading and target_witness in reading['SR_text']:
            return [x[target_witness] for x in reading['SR_text'][target_witness]['text']]
        if len(reading['text']) > 0 and target_witness in reading['text'][0]:
            return [x[target_witness] for x in reading['text']]
        if 'subreadings' in reading:
            for type in reading['subreadings']:
                for subreading in reading['subreadings'][type]:
                    if target_witness in subreading['witnesses']:
                        return [x[target_witness] for x in subreading['text']]
        # hands have already been filtered when we run this so check again with firsthand marker
        if suffix is None:
            return self.get_representative_witness_token_list(reading, '*')
        return []

    # replaces a function in exporter.py with specific MUYA features
    # such as turning 'not expected' into 'not exp.'
    def get_text(self, reading, type=None):
        if type == 'subreading':
            return self.get_text_from_text_string(reading)
        if len(reading['text']) > 0:
            if 'text_string' in reading:
                return self.get_text_from_text_string(reading)
            return self.get_text_from_text_list(reading)
        else:
            if 'overlap_status' in reading.keys() and (reading['overlap_status'] in ['overlapped', 'deleted']):
                text = ['', reading['overlap_status']]
            elif 'type' in reading.keys() and reading['type'] in ['om_verse', 'om']:
                if 'details' in reading.keys():
                    if reading['details'] == 'not expected':
                        text = ['&notexp;', reading['type']]
                    elif reading['details'].find('gap') == 0 or reading['details'].find('ill') == 0:
                        text = ['&nonleg;', reading['type']]
                    elif reading['details'].find('lac') == 0:
                        text = ['&lac;', reading['type']]
                    elif reading['details'] == 'om':
                        text = ['&om;', reading['type']]
                    else:
                        text = [reading['details'], reading['type']]
                else:
                    text = ['om.', reading['type']]
            elif 'type' in reading.keys() and reading['type'] in ['lac_verse', 'lac']:
                if 'details' in reading.keys():
                    if reading['details'] == 'not expected':
                        text = ['&notexp;', reading['type']]
                    elif reading['details'] == 'abbreviated text':
                        text = ['&abbr;', reading['type']]
                    elif reading['details'] == 'supplied abbreviated text':
                        text = ['&suppliedabbr;', reading['type']]
                    elif reading['details'].find('gap') == 0 or reading['details'].find('ill') == 0:
                        text = ['&nonleg;', reading['type']]
                    elif reading['details'].find('lac') == 0:
                        text = ['&lac;', reading['type']]
                    else:
                        text = [reading['details'], reading['type']]
                else:
                    text = ['&lac;', reading['type']]
        return text

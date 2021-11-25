# -*- coding: utf-8 -*-
import re
from io import StringIO
from lxml import etree
from collation.yasna_exporter import YasnaExporter
from collation.exceptions import DataStructureError


class LatexExporter(YasnaExporter):

    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0', 'xml': 'http://www.w3.org/XML/1998/namespace'}

    def export_data(self, data):

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

        return self.get_latex_output(xml, self.settings)

    def get_doctype(self):
        doctype = ('<!DOCTYPE TEI [ '
                   '<!ENTITY lac "lac."> '
                   '<!ENTITY om "om."> '
                   '<!ENTITY abbr "abbr."> '
                   '<!ENTITY suppliedabbr "supplied abbr."> '
                   '<!ENTITY notexp "not exp."> '
                   '<!ENTITY nonleg "non leg."> '
                   ']>')
        return doctype

    def get_witness_subgroups(self, witness_list, classification):
        latex = []
        if classification == 'Y':
            split_point = 100
        elif classification == 'PY':
            split_point = 500
        elif classification == 'VS':
            split_point = 4200
        sg_1 = []
        sg_2 = []
        for witness in witness_list:
            match = re.match(r'(\d+)\D*', witness)
            numerical_siglum = int(match.group(1))
            if numerical_siglum < split_point:
                sg_1.append(witness)
            else:
                sg_2.append(witness)
        if len(sg_1) > 0:
            latex.append('\\witsubclass{')
            for wit in sg_1:
                latex.append('\\wit{{{0}}}'.format(wit))
            latex.append('}')
        if len(sg_2) > 0:
            latex.append('\\witsubclass{')
            for wit in sg_2:
                latex.append('\\wit{{{0}}}'.format(wit))
            latex.append('}')
        return ''.join(latex)

    def get_witness_groups(self, witnesses):
        latex = []
        classified_witnesses = {}
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

        for i, label in enumerate(classified_witnesses):
            if i > 0:
                latex.append('%\n')
            latex.append('\\witclass{')
            if label in ['Y', 'PY', 'VS']:
                latex.append(self.get_witness_subgroups(classified_witnesses[label], label))
            else:
                for wit in classified_witnesses[label]:
                    latex.append('\\wit{{{0}}}'.format(wit))
            latex.append('}')
        return ''.join(latex)

    def get_lemma_text(self, overtext, start, end):
        if start == end and start % 2 == 1:
            return ['', 'om']
        real_start = int(start/2)-1
        real_end = int(end/2)-1
        if 'type' in overtext['tokens'][real_start]:
            type = overtext['tokens'][real_start]['type']
        else:
            type = None
        word_list = []
        for token in overtext['tokens']:
            if 'language' not in token or token['language'] == self.main_language:
                word_list.append(token['original'])
            else:
                word_list.append('\\foreign[{0}]{{{1}}}'.format(token['language'], token['original']))
        if type is not None:
            return [' '.join(word_list[real_start:real_end+1]), type]
        return [' '.join(word_list[real_start:real_end+1])]

    def get_latex_output(self, xml, settings):

        parser = etree.XMLParser(resolve_entities=True)
        tree = etree.parse(StringIO(xml.replace('<?xml version="1.0" encoding="utf-8"?>', '')), parser)

        latex = []
        for stanza in tree.xpath('.//tei:div[@type="stanza"]', namespaces=self.namespaces):
            latex.append('\\begin{stanza}')
            full_reference = stanza.get('{http://www.w3.org/XML/1998/namespace}id').replace('-APP', '')
            ceremony, reference = full_reference.split('.', 1)
            latex.append(r'{{\{0}{{{1}}}}}'.format(ceremony, reference))
            for app in stanza.xpath('.//tei:app',  namespaces=self.namespaces):
                unit_context = app.get('n')
                if self.book_prefix and unit_context[0] == self.book_prefix:
                    unit_context = unit_context[1:]
                if app.get('type') == 'main':
                    lemma = app.xpath('.//tei:lem', namespaces=self.namespaces)[0]
                    type = lemma.get('type')
                    if type is None:
                        latex.append('\n')
                        latex.append('\\editedtext{{{0}}}'.format(self.process_reading_text(lemma.text)))
                    else:
                        latex.append('\n')
                        latex.append('\\edited{0}text{{{1}}}'.format(type, self.process_reading_text(lemma.text)))
                    if ('include_apparatus' not in settings
                            or (settings['include_apparatus'] is True
                                and unit_context not in settings['omit_apparatus'])):
                        latex.append('\\app{')
                        for i, rdg in enumerate(app.xpath('.//tei:rdg', namespaces=self.namespaces)):
                            if i > 0:
                                latex.append('%\n')
                            if rdg.get('type') == 'subreading':
                                latex.append('\\rdg[{}][{}]{{'.format(rdg.get('cause'),
                                                                      self.get_label(rdg.get('cause'))))
                            else:
                                latex.append('\\rdg{')
                            latex.append(self.get_witness_groups(self.get_witness_list(rdg)))
                            latex.append('}')
                            latex.append('{{{0}}}'.format(self.process_reading_text(rdg.text)))

                        latex.append('}')
                        if app.getnext() is not None and app.getnext().tag == '{http://www.tei-c.org/ns/1.0}lb':
                            latex.append('%\n')
                        else:
                            latex.append('\n')

                if app.get('type') == 'ritual_direction':
                    if ('ritual_directions' not in settings):
                        pass
                    elif (settings['ritual_directions'] == 'transliteration'):
                        if app.get('rend', None) == 'no_linebreak':
                            latex.append('\\rd*{{{0}}}'.format(self.process_rd_text(app.xpath('.//tei:lem[@type="transliteration"]',
                                                                                              namespaces=self.namespaces
                                                                                              )[0].text)))
                        else:
                            latex.append('\n')
                            latex.append('\\rd{{{0}}}'.format(self.process_rd_text(app.xpath('.//tei:lem[@type="transliteration"]',
                                                                                             namespaces=self.namespaces
                                                                                             )[0].text)))
                    elif settings['ritual_directions'] == 'transcription':
                        text = self.process_rd_text(app.xpath('.//tei:lem[@type="transcription"]',
                                                              namespaces=self.namespaces
                                                              )[0].text)
                        text = self.add_avestan_tags(text)
                        if app.get('rend', None) == 'no_linebreak':
                            latex.append('\\rd*{{{0}}}'.format(text))
                        else:
                            latex.append('\n')
                            latex.append('\\rd{{{0}}}'.format(text))
                    if app.getnext() is not None and app.getnext().tag == '{http://www.tei-c.org/ns/1.0}lb':
                        latex.append('%\n')
                    else:
                        latex.append('\n')
                if app.getnext() is not None and app.getnext().tag == '{http://www.tei-c.org/ns/1.0}lb':
                    latex.append('\\newline')
            latex.append('\\end{stanza}')
            latex.append('\n')
        latex_string = ''.join(latex)
        latex_string = latex_string.replace('\n\n', '\n')
        return latex_string

    # NB: the order of this really matters
    def process_reading_text(self, text):
        text = self.fix_special_combine_letters(text)
        text = self.mark_special_readings(text)
        return text

    # NB: the order of this really matters
    def process_rd_text(self, text):
        text = text.replace('\\', '\\newline')
        text = self.escape_latex_characters(text)
        text = self.fix_special_combine_letters(text)
        return text

    def mark_special_readings(self, text):
        if text == 'abbr.':
            return '\\gls{abbr}'
        if text == 'supplied abbr.':
            return '\\gls{suppliedabbr}'
        if text == 'not exp.':
            return '\\gls{notexp}'
        if text == 'non leg.':
            return '\\gls{nonleg}'
        if text == 'lac.':
            return '\\gls{lac}'
        if text == 'om.':
            return '\\gls{om}'
        return text

    def fix_special_combine_letters(self, text):
        if not text:
            return text
        # first two used by celine last two by chiara
        # although these look the same the first 2 examples have a special
        # space character between them ord 8203 in python
        if 'x​ͮ' not in text and 'ŋ​ͮ' not in text and 'xͮ' not in text and 'ŋͮ' not in text:
            return text
        text = text.replace('x​ͮ', '\\XVE{}').replace('ŋ​ͮ', '\\NGVE{}')
        text = text.replace('xͮ', '\\XVE{}').replace('ŋͮ', '\\NGVE{}')
        return text

    def get_witness_list(self, rdg):
        witnesses = []
        for wit in rdg.xpath('./tei:wit/tei:idno', namespaces=self.namespaces):
            witnesses.append(self.process_witness(wit.text))
        return witnesses

    def process_witness(self, text):
        if 'sec.m.' not in text:
            return text
        text = text.replace('sec.m.', '\\gls{secmanu}')
        return text

    def escape_latex_characters(self, text):
        text = text.replace('\\(?!newline)', '\\textbackslash{}')
        text = text.replace('{', '\\{').replace('}', '\\}')
        text = text.replace('#', '\\#')
        text = text.replace('$', '\\$')
        text = text.replace('_', '\\_')
        text = text.replace('^', '\\^')
        text = text.replace('&', '\\&')
        text = text.replace('%', '\\%')
        text = text.replace('~', '\\textasciitilde{}')
        return text

    def add_avestan_tags(self, text):
        if '[ave]' not in text:
            return text
        m = re.search(r'\[/ave\]', text)
        if not m:
            return text
        text = text.replace('[ave]', '\\Avst{').replace('[/ave]', '}')
        return text

    def add_latex_reading_macros(self, text):
        text = text.replace('&lt;abbreviated text&gt;', '\\gls{abbr}')
        text = text.replace('&lt;supplied abbreviated text&gt;', '\\gls{suppliedabbr}')
        pattern = re.compile(r'&lt;ill\s?[^&]*?&gt;')
        text = pattern.sub(r'\\gls{nonleg}', text)
        pattern = re.compile(r'&lt;gap\s?[^&]*?&gt;')
        text = pattern.sub(r'\\gls{nonleg}', text)
        pattern = re.compile(r'&lt;lac\s?[^&]*?&gt;')
        text = pattern.sub(r'\\gls{lac}', text)
        return text

    # This makes the following assumptions (but I think they are all correct)
    # 1) that the foreign tags in the first witness (reading the main reading not a hidden subreading unless that is
    #   the only witness) will be true for all witnesses in this reading
    # 2) that if the witness text length is different from the reading split on spaces:
    #   2a) all foreign if all text list tokens are foreign
    #   2b) all are not foreign if some of the list tokens are not
    # 3) that no word has been regularised to another language at the RG stage
    def get_text_from_text_string(self, reading):
        original_tokens = self.get_representative_witness_token_list(reading)
        # first convert any special categories into latex macros
        text_string = reading['text_string']
        if '&lt;' in text_string:
            text_string = self.add_latex_reading_macros(text_string)
        reading_tokens = text_string.split(' ')
        reading_text = []
        if len(original_tokens) == len(reading_tokens):
            # then we add foreign tags by word
            for i, token in enumerate(original_tokens):
                if reading_tokens[i].find('\\gls') != -1:
                    reading_text.append(reading_tokens[i])
                else:
                    escaped_token = self.escape_latex_characters(reading_tokens[i].replace('&lt;', '<')
                                                                                  .replace('&gt;', '>'))
                    if 'foreign' in token and token['foreign'] is True:
                        reading_text.append('\\foreign[{}]{{{}}}'.format(token['language'] if 'language' in token
                                                                         else '', escaped_token))
                    else:
                        reading_text.append(escaped_token)
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
                if token.find('\\gls') != -1:
                    reading_text.append(token)
                else:
                    escaped_token = self.escape_latex_characters(token.replace('&lt;', '<').replace('&gt;', '>'))
                    if add_foreign_tags is False:
                        reading_text.append(escaped_token)
                    elif add_language is False:
                        reading_text.append('\\foreign[]{{{}}}'.format(escaped_token))
                    else:
                        reading_text.append('\\foreign[{}]{{{}}}'.format(other_language, escaped_token))

        return [' '.join(reading_text)]

    def get_label(self, classes):
        label = []
        if 'orthographic' in classes:
            label.append('o')
        if 'phonetic' in classes:
            label.append('p')
        if 'reconstructed' in classes:
            label.append('r')
        label_text = ''.join(label)
        if label_text == 'o':
            return '\\gls{ortho}'
        if label_text == 'or':
            return '\\gls{orthorec}'
        if label_text == 'op':
            return '\\gls{orthophone}'
        if label_text == 'opr':
            return '\\gls{orthophonerec}'
        if label_text == 'p':
            return '\\gls{phone}'
        if label_text == 'pr':
            return '\\gls{phonerec}'
        if label_text == 'r':
            return '\\gls{rec}'
        return label_text

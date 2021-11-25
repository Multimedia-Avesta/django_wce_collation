from lxml import etree
from transcriptions.yasna_word_parser import YasnaWordParser


class RitualDirectionExtractor(object):

    def __init__(self):
        self.word_parser = YasnaWordParser()
        self.parser = etree.XMLParser(resolve_entities=False)
        self.sigla = []
        self.ritual_dirs = {}
        self.y_n_values = []
        self.vrs_n_values = []
        self.vs_n_values = []
        self.vyts_n_values = []
        self.yvr_n_values = []
        self.errors = []

    def get_ritual_direction_text(self, rd, verse):
        rd_wrapper = etree.Element('wrapper')
        rd_wrapper.append(rd)
        data = self.word_parser.walk_reading(rd_wrapper,  verse, '')

        if len(data[0]) > 0:
            new_list = []
            for word in data[0]:
                if 'gap_before_details' in word:
                    new_list.append('<{}>'.format(word['gap_before_details']))
                if 'pc_before' in word and 'pc_after' in word:
                    new_list.append('{}{}{}'.format(word['pc_before'], word['original'], word['pc_after']))
                elif 'pc_before' in word:
                    new_list.append('{}{}'.format(word['pc_before'], word['original']))
                elif 'pc_after' in word:
                    new_list.append('{}{}'.format(word['original'], word['pc_after']))
                else:
                    new_list.append(word['original'])
                if 'gap_after_details' in word:
                    new_list.append('<{}>'.format(word['gap_after_details']))
            return ' '.join(new_list)

        return ''

    def extract_ritual_directions(self, transcriptions):
        for transcription in transcriptions:
            tree = etree.XML(transcription['tei'], self.parser)
            siglum = transcription['siglum']

            if siglum != 'basetext':
                self.sigla.append(siglum)
            self.ritual_dirs[siglum] = {}
            for rd in tree.xpath('//tei:ab[@type="ritualdirection"]',
                                 namespaces={'tei': 'http://www.tei-c.org/ns/1.0'}):
                n = rd.get('n')
                book = n.split('.')[0]
                if book == 'Y' and n not in self.y_n_values:
                    self.y_n_values.append(n)
                elif book == 'VrS' and n not in self.vrs_n_values:
                    self.vrs_n_values.append(n)
                elif book == 'VS' and n not in self.vs_n_values:
                    self.vs_n_values.append(n)
                elif book == 'VytS' and n not in self.vyts_n_values:
                    self.vyts_n_values.append(n)
                elif book == 'YVr' and n not in self.yvr_n_values:
                    self.yvr_n_values.append(n)
                elif book not in ['Y', 'VrS', 'VS', 'VytS', 'YVr']:
                    self.errors.append('book {} in unit {} not recognised'.format(book, n))

                text = self.get_ritual_direction_text(rd, {'siglum': siglum})
                if n in self.ritual_dirs[siglum]:
                    self.ritual_dirs[siglum][n].append(text)
                else:
                    self.ritual_dirs[siglum][n] = [text]

        n_list = sorted(self.y_n_values, key=lambda x: (x.split('.')[0],
                                                        int(x.split('.')[1]),
                                                        int(x.split('.')[2]),
                                                        int(x.split('.')[3])
                                                        )
                        )
        n_list.extend(sorted(self.vrs_n_values, key=lambda x: (x.split('.')[0],
                                                               int(x.split('.')[1]),
                                                               int(x.split('.')[2]),
                                                               int(x.split('.')[3])
                                                               )
                             )
                      )
        n_list.extend(sorted(self.vs_n_values, key=lambda x: (x.split('.')[0],
                                                              int(x.split('.')[1]),
                                                              int(x.split('.')[2]),
                                                              int(x.split('.')[3])
                                                              )
                             )
                      )
        n_list.extend(sorted(self.vyts_n_values, key=lambda x: (x.split('.')[0],
                                                                int(x.split('.')[1]),
                                                                int(x.split('.')[2]),
                                                                int(x.split('.')[3])
                                                                )
                             )
                      )
        n_list.extend(sorted(self.yvr_n_values, key=lambda x: (x.split('.')[0],
                                                               int(x.split('.')[1]),
                                                               int(x.split('.')[2]),
                                                               int(x.split('.')[3])
                                                               )
                             )
                      )

        self.sigla = sorted(self.sigla, key=lambda x: (float(x.replace('S', '.5'))))
        self.sigla.append('basetext')

        return (self.ritual_dirs, self.sigla, n_list, self.errors)

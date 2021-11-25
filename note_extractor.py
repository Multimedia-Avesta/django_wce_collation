from lxml import etree


class NoteExtractor(object):

    def __init__(self):
        self.parser = etree.XMLParser(resolve_entities=False)
        self.sigla = []
        self.notes = {}

    def get_closest_n(self, note):
        try:
            ab = note.xpath('./ancestor::tei:ab', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]
            return ab.get('n')
        except (KeyError, IndexError):
            try:
                div = note.xpath('./ancestor::tei:div', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]
                return div.get('n')
            except (KeyError, IndexError):
                return 'location not found'

    def extract_notes(self, transcriptions):
        for transcription in transcriptions:
            tree = etree.XML(transcription['tei'], self.parser)
            siglum = transcription['siglum']

            if siglum != 'basetext':
                self.sigla.append(siglum)
            self.notes[siglum] = []
            for note in tree.xpath('//tei:note',
                                   namespaces={'tei': 'http://www.tei-c.org/ns/1.0'}):
                n = self.get_closest_n(note)
                self.notes[siglum].append([n, note.text])
        self.sigla = sorted(self.sigla, key=lambda x: (float(x.replace('S', '.5'))))

        return (self.notes, self.sigla)

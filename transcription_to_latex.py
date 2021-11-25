import os
from lxml import etree
from django.conf import settings as django_settings


class TranscriptionConverter(object):

    def __init__(self):
        self.parser = etree.XMLParser(resolve_entities=False)

    def convert_transcription(self, transcription):
        tree = etree.XML(transcription, self.parser)
        siglum = tree.xpath('//tei:title[@type="document"]/@n',
                            namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]

        xsl_path = os.path.join(django_settings.BASE_DIR, 'collation', 'xslt', 'transcription_to_latex.xsl')
        if os.path.exists(xsl_path):
            xsl_string = open(xsl_path, mode='r', encoding='utf-8').read()
            xsl_string = xsl_string.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            xsl_tree = etree.XML(xsl_string)
            xsl_transformer = etree.XSLT(xsl_tree)
        else:
            raise

        result = xsl_transformer(tree)
        latex = str(result)
        latex = latex.replace('x​ͮ', '\\XVE{}').replace('ŋ​ͮ', '\\NGVE{}')
        latex = latex.replace('xͮ', '\\XVE{}').replace('ŋͮ', '\\NGVE{}')

        return (latex, siglum)

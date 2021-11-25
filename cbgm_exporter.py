import re
from collation.yasna_exporter import YasnaExporter
from collation.exceptions import DataStructureError


class CBGMExporter(YasnaExporter):

    def export_data(self, data):

        # sometimes the data doesn't seem to be correct so check for this first
        if 'structure' not in data[0]:
            raise DataStructureError('There was a problem accessing the data. Please try again.')

        data = self.remove_intraceremony_references(data)
        # never add a raised plus for the CBGM
        self.add_raised_plus = False
        self.sigla_lookup, self.hand_list = self.create_sigla_lookup_and_hand_list(data)
        self.hand_order_lookup = self.create_hand_order_lookup(self.sigla_lookup)
        data = self.merge_lac_readings(data)
        filtered_data = self.filter_hands(data)
        filtered_data = self.remove_repeats(filtered_data)
        # fix the labels because anything that is after lac in the interface won't have one and they might have
        # been reordered
        filtered_data = self.fix_labels(filtered_data)
        # now always merge sigla and suffixes
        filtered_data = self.merge_sigla_and_suffixes(filtered_data)
        # filter any supplements and related transcriptions
        # turned off for CBGM because I think it will break it
        # filtered_data = self.filter_supplements(filtered_data, settings)
        xml = self.get_structured_xml(filtered_data)

        if self.settings:
            xml = self.apply_settings(xml, self.settings)
            xml = self.fix_v_encoding(xml)
            return xml
        xml = self.fix_v_encoding(xml)
        return xml

    def remove_intraceremony_references(self, data):
        intraceremony_regex = re.compile(r'^\S+?\s\(\S+?\.\d+\.\d+\.\d+\)$')

        for entry in data:
            context = entry['context']
            for key in entry['structure']:
                if key.find('apparatus') != -1:
                    for unit in entry['structure'][key]:
                        for i, reading in enumerate(unit['readings']):
                            for j in range(len(reading['witnesses'])-1, -1, -1):
                                if re.match(intraceremony_regex, reading['witnesses'][j]) is not None:
                                    del reading['witnesses'][j]
                                    del reading['suffixes'][j]

                            if 'subreadings' in reading:
                                types_to_delete = []
                                for type in reading['subreadings']:
                                    for j, subreading in enumerate(reading['subreadings'][type]):
                                        for k in range(len(subreading['witnesses'])-1, -1, -1):
                                            if re.match(intraceremony_regex, subreading['witnesses'][k]) is not None:
                                                del subreading['witnesses'][k]
                                                del subreading['suffixes'][k]
                                        if len(subreading['witnesses']) == 0:
                                            reading['subreadings'][type][j] = None
                                    reading['subreadings'][type] = [sr for sr in reading['subreadings'][type]
                                                                    if sr is not None]
                                    if len(reading['subreadings'][type]) == 0:
                                        types_to_delete.append(type)
                                for type in types_to_delete:
                                    del reading['subreadings'][type]
                                if len(reading['subreadings'].keys()) == 0:
                                    del reading['subreadings']

                            if len(reading['witnesses']) == 0 and 'subreadings' not in reading:
                                unit['readings'][i] = None
                        unit['readings'] = [r for r in unit['readings'] if r is not None]

        return data

    def remove_repeats(self, data):
        repeat_regex = re.compile(r'^(\S+?)-(\d+?)(\D*?)$')
        for entry in data:
            context = entry['context']
            for key in entry['structure']:
                if key.find('apparatus') != -1:
                    for unit in entry['structure'][key]:
                        for i, reading in enumerate(unit['readings']):
                            for j in range(len(reading['witnesses'])-1, -1, -1):
                                m = re.match(repeat_regex, reading['witnesses'][j])
                                if m is not None:
                                    if m.group(2) == '1':
                                        if m.group(3) not in ['']:
                                            reading['witnesses'][j] = '{}{}'.format(m.group(1), m.group(3))
                                        else:
                                            reading['witnesses'][j] = m.group(1)
                                    else:
                                        del reading['witnesses'][j]
                                        del reading['suffixes'][j]

                            if 'subreadings' in reading:
                                types_to_delete = []
                                for type in reading['subreadings']:
                                    for j, subreading in enumerate(reading['subreadings'][type]):
                                        for k in range(len(subreading['witnesses'])-1, -1, -1):
                                            m = re.match(repeat_regex, subreading['witnesses'][k])
                                            if m is not None:
                                                if m.group(2) == '1':
                                                    if m.group(3) not in ['']:
                                                        subreading['witnesses'][k] = '{}{}'.format(m.group(1),
                                                                                                   m.group(3))
                                                    else:
                                                        subreading['witnesses'][k] = m.group(1)
                                                else:
                                                    del subreading['witnesses'][k]
                                                    del subreading['suffixes'][k]
                                        if len(subreading['witnesses']) == 0:
                                            reading['subreadings'][type][j] = None
                                    reading['subreadings'][type] = [sr for sr in reading['subreadings'][type]
                                                                    if sr is not None]
                                    if len(reading['subreadings'][type]) == 0:
                                        types_to_delete.append(type)
                                for type in types_to_delete:
                                    del reading['subreadings'][type]
                                if len(reading['subreadings'].keys()) == 0:
                                    del reading['subreadings']

                            if len(reading['witnesses']) == 0 and 'subreadings' not in reading:
                                unit['readings'][i] = None
                        unit['readings'] = [r for r in unit['readings'] if r is not None]
        return data

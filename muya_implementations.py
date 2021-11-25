# -*- coding: utf-8 -*-
import re


class RuleConditions(object):

    def ignore_unclear(self, decision_word, token_words):
        decision_word = decision_word.replace('{', '').replace('}', '')
        token_words = [w.replace('{', '').replace('}', '') for w in token_words]
        return(decision_word, token_words)

    def ignore_supplied(self, decision_word, token_words):
        decision_word = re.sub(r'\[(?!\d)', '', re.sub(r'(?<!\d)\]', '', decision_word))
        token_words = [re.sub(r'\[(?!\d)', '', re.sub(r'(?<!\d)\]', '', w)) for w in token_words]
        return(decision_word, token_words)


class ApplySettings(object):

    def select_lemma(self, token):
        if 'lemma' in token:
            token['interface'] = token['lemma']
        return token

    def lower_case(self, token):
        if len(token['interface']) > 0:
            token['interface'] = token['interface'].lower()
            return token
        else:
            return token

    def expand_abbreviations(self, token):
        if 'n' in token:  # applied rules trump this setting
            token['interface'] = token['n']
        elif 'expanded' in token:
            token['interface'] = token['expanded']
        return token

    def hide_supplied_text(self, token):
        token['interface'] = re.sub(r'\[(?!\d)', '', re.sub(r'(?<!\d)\]', '', token['interface']))
        return token

    def hide_unclear_text(self, token):
        token['interface'] = token['interface'].replace('{', '').replace('}', '')
        return token

    def show_punctuation(self, token):
        if 'pc_before' in token:
            token['interface'] = '{}{}'.format(token['pc_before'], token['interface'])
        if 'pc_after' in token:
            token['interface'] = '{}{}'.format(token['interface'], token['pc_after'])
        return token

# -*- coding: utf-8 -*-

import re

capital_letters = {'А': 'A',
                   'Б': 'B',
                   'В': 'V',
                   'Г': 'G',
                   'Д': 'D',
                   'Е': 'E',
                   'Ё': 'E',
                   'З': 'Z',
                   'И': 'I',
                   'Й': 'Y',
                   'К': 'K',
                   'Л': 'L',
                   'М': 'M',
                   'Н': 'N',
                   'О': 'O',
                   'П': 'P',
                   'Р': 'R',
                   'С': 'S',
                   'Т': 'T',
                   'У': 'U',
                   'Ф': 'F',
                   'Х': 'H',
                   'Ъ': '',
                   'Ы': 'Y',
                   'Ь': '',
                   'Э': 'E', }

capital_letters_transliterated_to_multiple_letters = {'Ж': 'Zh',
                                                      'Ц': 'Ts',
                                                      'Ч': 'Ch',
                                                      'Ш': 'Sh',
                                                      'Щ': 'Sch',
                                                      'Ю': 'Yu',
                                                      'Я': 'Ya', }

lower_case_letters = {'а': 'a',
                      'б': 'b',
                      'в': 'v',
                      'г': 'g',
                      'д': 'd',
                      'е': 'e',
                      'ё': 'e',
                      'ж': 'zh',
                      'з': 'z',
                      'и': 'i',
                      'й': 'y',
                      'к': 'k',
                      'л': 'l',
                      'м': 'm',
                      'н': 'n',
                      'о': 'o',
                      'п': 'p',
                      'р': 'r',
                      'с': 's',
                      'т': 't',
                      'у': 'u',
                      'ф': 'f',
                      'х': 'h',
                      'ц': 'ts',
                      'ч': 'ch',
                      'ш': 'sh',
                      'щ': 'sch',
                      'ъ': '',
                      'ы': 'y',
                      'ь': '',
                      'э': 'e',
                      'ю': 'yu',
                      'я': 'ya', }


def transliterate(string):
    for cyrillic_string, latin_string in capital_letters_transliterated_to_multiple_letters.items():
        string = re.sub("%s([а-я])" % cyrillic_string, '%s\1' % latin_string, string)

    for dictionary in (capital_letters, lower_case_letters):

        for cyrillic_string, latin_string in dictionary.items():
            string = re.sub(cyrillic_string, latin_string, string)

    for cyrillic_string, latin_string in capital_letters_transliterated_to_multiple_letters.items():
        string = re.sub(cyrillic_string, latin_string.upper(), string)

    return string


def replace_non_alphabetic_symbols(string):
    string = re.sub(r'\W', '_', string)
    return string

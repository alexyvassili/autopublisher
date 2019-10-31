import requests


def send_line_to_yandex(line):
    response = requests.post('https://speller.yandex.net/services/spellservice.json/checkText',
                             data={'text': line})
    return response.json()


def fix_mispell(text, mispell):
    fix = mispell['s'][0]
    start = mispell['pos']
    end = mispell['pos'] + mispell['len']
    return text[:start] + fix + text[end:]


def spell_line(line):
    mispells = send_line_to_yandex(line)
    for mispell in mispells:
        line = fix_mispell(line, mispell)
    return line

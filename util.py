import difflib
import os
import re
from IPython.display import HTML
from jiwer import wer, cer


def read_transcript_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:  # encoding='utf-8'
        return file.read()


def clean_text(text):
    punctuation_before = '!),/:;>?]}»'
    punctuation_after = '([{«<'
    symbols_to_drop = r'"#\$%&^_`~\'\+\*-=@|'

    pattern_before = re.compile(r'\s([' + re.escape(punctuation_before) + '])')
    text = pattern_before.sub(r'\1', text)

    pattern_after = re.compile(r'([' + re.escape(punctuation_after) + '])\s')
    text = pattern_after.sub(r'\1', text)

    pattern_drop = re.compile('[' + re.escape(symbols_to_drop) + ']')
    text = pattern_drop.sub('', text)

    return text


def clean_text_for_comparison(input_text):
    def add_space_after_punctuation(input_text):
        punctuation = '!),:;>?]}'
        for char in punctuation:
            input_text = input_text.replace(char, char + " ")
        return input_text

    cleaned_input_text = clean_text(input_text)
    text_with_spaces = add_space_after_punctuation(cleaned_input_text)
    text_with_spaces = text_with_spaces.replace("\n", "\n ")

    text_with_spaces = ' '.join(text_with_spaces.splitlines())

    cleaned_text = ' '.join(text_with_spaces.split())

    return cleaned_text


def german_written_number_to_numeric(word):
    german_numbers_ones = {
        "null": 0, "eins": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
        "sechs": 6, "sieben": 7, "acht": 8, "neun": 9}
    german_numbers_teens = {"zehn": 10, "elf": 11, "zwölf": 12,
                            "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17,
                            "achtzehn": 18, "neunzehn": 19}
    german_numbers_tens = {"zwanzig": 20, "dreißig": 30, "vierzig": 40,
                           "fünfzig": 50, "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90
                           }

    german_numbers_hun = {"hundert": 100, "einhundert": 100, "zweihundert": 200,
                          "dreihundert": 300, "vierhundert": 400, "fünfhundert": 500, "sechshundert": 600,
                          "siebenhundert": 700, "achthundert": 800, "neunhundert": 900}
    german_numbers_hun_large = {
        "elfhundert": 1100,
        "zwölfhundert": 1200, "dreizehnhundert": 1300, "vierzehnhundert": 1400,
        "fünfzehnhundert": 1500,
        "sechzehnhundert": 1600, "siebzehnhundert": 1700, "achtzehnhundert": 1800,
        "neunzehnhundert": 1900}

    german_numbers_other = {"tausend": 1000,
                            "eintausend": 1000}

    def process_below_thousand(word):
        count = 0
        if word == "":
            return 0
        if word.startswith("und"):  # remove possible "und"
            word = word[3:]
        for prefix, number in german_numbers_hun.items():
            if word.startswith(prefix):
                count += number
                tens = process_below_hundred(word.split(prefix)[1])
                if tens >= 0:
                    return count + tens
                else:
                    return -1
        return process_below_hundred(word)

    def process_below_hundred(word):
        count = 0
        if word == "":
            return 0
        if word.startswith("und"):  # remove possible "und"
            word = word[3:]
        parts = word.split("und")
        if len(parts) == 1:
            for prefix, number in {**german_numbers_tens, **german_numbers_teens, **german_numbers_ones}.items():
                if word == prefix:
                    return number
            return -1
        elif len(parts) == 2:  # compound number such as fünfundvierzig
            ones, tens = parts
            for prefix, number in german_numbers_ones.items():
                if ones == prefix:
                    count += number
                    for prefix_tens, number_tens in german_numbers_tens.items():
                        if tens == prefix_tens:
                            return count + number_tens
                    return -1
            return -1
        else:
            return -1

    word = word.lower()

    total = 0

    # Try  ...hundert
    for prefix, number in {**german_numbers_hun, **german_numbers_hun_large}.items():
        if word.startswith(prefix):
            total += number
            tens = process_below_hundred(word.split(prefix)[1])
            if tens >= 0:
                total += tens
                return str(total)

    # try ...tausend
    for prefix, number in german_numbers_other.items():
        if word.startswith(prefix):
            huns = process_below_thousand(word.split(prefix)[1])
            if huns >= 0:
                total += huns
                return str(total)

    # try ein, zwei, ...
    for prefix, number in german_numbers_ones.items():
        if word.startswith(prefix):
            parts = word.split(prefix)
            if len(parts) == 1:
                for prefix_tens, number_tens in german_numbers_tens.items():
                    if tens == prefix_tens:
                        total += tens
                        return str(total)
            else:
                if parts[1].startswith("tausend"):
                    total = number * 1000
                    parts_huns = parts[1].split("tausend")
                    huns = process_below_thousand(parts_huns[1])
                    if huns >= 0:
                        total += huns
                        return str(total)

    # 11, 12, ...
    tens = process_below_hundred(word)
    if tens >= 0:
        return str(tens)

    return word


def replace_punctuation(text):
    punctuation = r'!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~»«' + ''.join([
        "-",  # Hyphen-minus
        "−",  # Minus sign
        "–",  # En dash
        "—",  # Em dash
        "⁻",  # Superscript minus
        "₋",  # Subscript minus
        "∓",  # Minus-or-plus sign
        "∸",  # Dot minus
        "≂",  # Minus tilde
        "⊖",  # Circled minus
        "⊟",  # Squared minus
        "➖",  # Heavy minus sign
        "﹣",  # Small hyphen-minus
        "－",  # Fullwidth hyphen-minus
    ])

    # Replace punctuation surrounded by spaces with €
    pattern_surrounded = r'\s([' + re.escape(punctuation) + r'])\s'
    text = re.sub(pattern_surrounded, ' € ', text)

    # Remove remaining punctuation
    pattern_remaining = r'[' + re.escape(punctuation) + r']'
    text = re.sub(pattern_remaining, '', text)

    return text


def eval(original_text, asr_text, type="wer"):
    eval_func = cer if type == "cer" else wer

    original_text = clean_text_for_comparison(original_text)
    asr_text = clean_text_for_comparison(asr_text)

    original_words = replace_punctuation(original_text).lower().split()
    original_words = [german_written_number_to_numeric(w) for w in original_words]
    original_text = " ".join(original_words)

    asr_words = replace_punctuation(asr_text).lower().split()
    asr_words = [german_written_number_to_numeric(w) for w in asr_words]
    asr_text = " ".join(asr_words)

    return eval_func(original_text, asr_text)


def diff_html(original_text, asr_text, filename):
    original_text = clean_text_for_comparison(original_text)
    asr_text = clean_text_for_comparison(asr_text)

    original_words = replace_punctuation(original_text).lower().split()
    original_words = [german_written_number_to_numeric(w) for w in original_words]
    original_words_unchanged = original_text.split()

    asr_words = replace_punctuation(asr_text).lower().split()
    asr_words = [german_written_number_to_numeric(w) for w in asr_words]
    asr_words_unchanged = asr_text.split()

    matcher = difflib.SequenceMatcher(None, asr_words, original_words)

    html_content = """<html><head><meta charset="UTF-8"><style>    
    .highlight-inserted {
      background: #7fff7f;
      text-decoration: none; /* Remove underline if desired */
    }
    .highlight-deleted {
      background: #ff7f7f;
      text-decoration: line-through; 
    }
    .highlight-deleted2 {
      background: #ffd27f;
      text-decoration: line-through;
    }
    .highlight-inserted2 {
      background: #7fdfff;      
    }</style></head>"""
    html_content += '<body><p>Legend:</p><ul>'
    html_content += '<li><span class="highlight-deleted">Wrong words (ASR)</span> that need to be replaced by <span class="highlight-inserted">correct words (from manual transcript)</span></li>'
    html_content += '<li><span class="highlight-deleted2">Words wrongly inserted by ASR</span></li>'
    html_content += '<li><span class="highlight-inserted2">Words missing in ASR</span></li>'
    html_content += '</ul>'

    html_content += '<p>Comparison:</p><p>'

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            html_content += '<span class="highlight-deleted">' + ' '.join(
                asr_words_unchanged[i] for i in range(i1, i2)) + '</span>'
            html_content += '<span class="highlight-inserted">' + ' '.join(
                original_words_unchanged[j] for j in range(j1, j2)) + '</span>'
        elif tag == 'delete':
            html_content += ' '.join(
                ['<span class="highlight-deleted2">' + asr_words_unchanged[i] + '</span>' for i in range(i1, i2)])
        elif tag == 'insert':
            html_content += ' '.join(
                ['<span class="highlight-inserted2">' + original_words_unchanged[j] + '</span>' for j in range(j1, j2)])
        elif tag == 'equal':
            html_content += ' '.join(original_words_unchanged[j1:j2])

        html_content += ' \n'
    html_content += '</p></body></html>'
    with open(filename, "w") as f:
        f.write(html_content)
    return HTML(html_content)


def timestamp_to_milliseconds(timestamp):
    """
    Convert a timestamp from "mm:ss" format to milliseconds.

    :param timestamp: String in the format "mm:ss"
    :return: Integer representing milliseconds
    """
    # Split the timestamp into minutes and seconds
    splits = timestamp.split(":")
    if len(splits) < 3:
        minutes, seconds = map(int, splits)
        hours = 0
    else:
        hours, minutes, seconds = map(int, splits)

    # Convert minutes to milliseconds and add seconds converted to milliseconds
    milliseconds = (hours * 60 * 60 + minutes * 60 + seconds) * 1000
    return milliseconds

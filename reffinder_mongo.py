# -*- coding: utf-8 -*-
import itertools
from rutermextract import TermExtractor
import io
import json
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from googletrans import Translator

translator = Translator()


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_green(text):
    print(bcolors.OKGREEN + text + bcolors.ENDC)


def print_warn(text):
    print(bcolors.WARNING + text + bcolors.ENDC)


def print_blue(text):
    print(bcolors.OKBLUE + text + bcolors.ENDC)


class Sentence:
    user_choise = 0
    text = ""
    keywords = []
    search_key = ""
    books = []
    endpoint = 0

    def __init__(self, text):
        self.text = text


import re

latex_sym = ['\\begin{itemize}',
             '\\chapter{',
             '\\section{',
             '\\label{',
             '\\item',
             '\\begin{enumerate}',
             '\\end{enumerate}',
             '\\end{itemize}',
             '\\subsection{',
             '}',
             '\\todo{',
             '\\begin{figure}',
             '\\centering',
             '\\includegraphics',
             '\\end{figure}',
             ]


def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def latex_clear(text):
    for pattern in latex_sym:
        text = text.replace(pattern, '')
    return text


caps = "([A-Z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov)"


def find_eng_words(text):
    res = ''
    for w in text.split(' '):
        if re.match("^[a-zA-Z?><;,{}[\]\-_+=!@#$%\^&*|'\s)]*$", w) != None:
            res += w + ' '
    return res


def split_into_sentences(text):
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    if "Ph.D" in text: text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub("\s" + caps + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
    text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]", "\\1<prd>\\2<prd>\\3<prd>", text)
    text = re.sub(caps + "[.]" + caps + "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
    text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
    text = re.sub(" " + caps + "[.]", " \\1<prd>", text)
    # if "”" in text: text = text.replace(".”","”.")
    if "\"" in text: text = text.replace(".\"", "\".")
    if "!" in text: text = text.replace("!\"", "\"!")
    if "?" in text: text = text.replace("?\"", "\"?")
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = sentences[:-1]
    sentences = [s.strip() for s in sentences]
    return sentences


import random

from pymongo import MongoClient
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.oai
books_collection = db['books']
from bs4 import BeautifulSoup
import requests
#session = requests.Session()


def get_bibtex_from_url(url):
    try:
        session = requests.Session()
        request = session.get(url)
        soup = BeautifulSoup(request.text, "lxml")
        bib_txt = soup.find('', {'id': 'bibtex'}).p.text
    except:
        return get_bibtex_from_url(url)
    return bib_txt

def get_bib_articles(text):
     try:
        cursor = books_collection.find({"$text": {"$search": text}},
                                   {'_txtscr': {'$meta': 'textScore'}})[:50]
        cursor = cursor.limit(50)
        cursor = cursor.sort([('_txtscr', {'$meta': 'textScore'})])
        cursor = cursor.limit(10)

        articles = []
        for art in cursor:
            if(not 'creator' in art):
                continue
            art['author'] = ' '.join(art['creator'])
            articles.append(art)
     except:
        return []

     return articles


term_extractor = TermExtractor()
imp_file = io.open('./text.txt', 'r', encoding="utf-8")
text = imp_file.read()
sents_text = split_into_sentences(text)
sents_text = [' '.join(sents_text[i:i + 2]) for i in range(0, len(sents_text), 2)]

sents = []
cur_sum = 0
for sent in sents_text:
    sent_obj = Sentence(sent)
    cur_sum += len(sent)
    sent_obj.endpoint = cur_sum + text[cur_sum:cur_sum+100].find('.')+1
    sent_obj.keywords = term_extractor(latex_clear(sent))
    if (len(sent_obj.keywords) == 0):
        continue
    sent_obj.keywords = list(filter(lambda x: len(x.normalized.split()) > 1, sent_obj.keywords))
    articles = []
    kw = ' '.join(x.normalized for x in sent_obj.keywords[:3])
    translated = translator.translate(kw, dest='en').text
    translated +=' ' + find_eng_words(sent)
    sent_obj.search_key = translated
    print_green(translated)
    articles = get_bib_articles(translated)

    # for key in sent_obj.keywords:
    #     keynorm = key.normalized
    #     print_blue(keynorm)
    #     translated = translator.translate(keynorm, dest='en').text
    #     print_green(translated)
    #     articles_now = get_bib_articles(translated)
    #     if (len(articles_now)):
    #         sent_obj.search_key += ', ' + translated
    #         articles += articles_now
    #     if (len(articles) > 6):
    #         break

    sent_obj.books = articles
    sents.append(sent_obj)

result = ""
bibresult = ""
db = BibDatabase()
for j, s in enumerate(sents):
    print(chr(27) + "[2J")
    print(s.text)
    print()
    print_warn(s.search_key)
    print()
    print_blue('0 Nothing')
    for i, b in enumerate(s.books):
        if ('author' in b) and ('title' in b):
            print_blue("%s " % (i + 1) + b['title'] + ' ' + b['author'])
        else:
            continue

    command = safe_cast(input("Choise:"), int, 0)
    if (command > len(s.books)):
        continue
    if (j == 0):
        startpoint = 0
    else:
        startpoint = sents[j - 1].endpoint
    endpoint = s.endpoint
    if (command == 0):
        result += text[startpoint:endpoint]
    else:
        chosed_book = s.books[command - 1]
        bib_txt = get_bibtex_from_url(chosed_book['identifier'][0])
        bib_id = re.findall("\{(.*?)\," ,bib_txt)[0]
        result += text[startpoint:endpoint] + ' \\cite{%s}\n' % bib_id
        bibresult += bib_txt + '\n'
    with open('./backup.txt', 'w') as bf:
        bf.write(result.encode('utf-8').strip())
result += text[endpoint:]

import time

writer = BibTexWriter()
with open('./' + time.strftime("%Y%m%d-%H%M%S") + '_bibtex.bib', 'w') as bibfile:
    bibfile.write(bibresult.encode('utf-8').strip())

with open('./' + time.strftime("%Y%m%d-%H%M%S") + '_result.txt', 'w') as resultfile:
    resultfile.write(result.encode('utf-8').strip())

# articles = scholar.main('-a="John Doe" --citation=bt')

pass

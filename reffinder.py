# -*- coding: utf-8 -*-
import itertools
from rutermextract import TermExtractor
import io
import os
import scholar
import bibsonomy
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


def get_bib_articles(text):
    try:

        rest = bibsonomy.REST("djbios", "25d3ca29d80c703cd02f74ba805cfefa")
        bib = bibsonomy.BibSonomy(rest)
        jsonstr = bib.rest._get("/posts?search=" + text + "&resourcetype=bibtex&start=0&end=3")
        jsono = json.loads(jsonstr)
        if not 'post' in jsono['posts']:
            return []
        articles = []

        for post in jsono['posts']['post']:
            bibtex = post['bibtex']
            bibtex['ENTRYTYPE'] = bibtex['entrytype']
            if bibtex['bibtexKey'] == 'noauthororeditor':
                bibtex['bibtexKey'] = 'no' + str(random.randint(0, 34638463368))
            bibtex['ID'] = bibtex['bibtexKey']
            articles.append(bibtex)
    except:
        return []
    return articles


term_extractor = TermExtractor()
imp_file = io.open('./text.txt', 'r', encoding="utf-8")
text = imp_file.read()
sents_text = split_into_sentences(text)
sents_text = [' '.join(sents_text[i:i + 2]) for i in range(0, len(sents_text), 2)]

sents = []
cur_sum = 0;
for sent in sents_text:
    sent_obj = Sentence(sent)
    cur_sum += len(sent)
    sent_obj.endpoint = cur_sum + text[cur_sum:cur_sum+100].find('.')+1
    sent_obj.keywords = term_extractor(latex_clear(sent))
    if (len(sent_obj.keywords) == 0):
        continue
    sent_obj.keywords = list(filter(lambda x: len(x.normalized.split()) > 1, sent_obj.keywords))
    sent_obj.search_key = ""

    articles = []
    for key in sent_obj.keywords:
        keynorm = key.normalized
        print_blue(keynorm)
        translated = translator.translate(keynorm, dest='en').text
        print_green(translated)
        articles_now = get_bib_articles(translated)
        if (len(articles_now)):
            sent_obj.search_key += ', ' + translated
            articles += articles_now
        if (len(articles) > 6):
            break

    sent_obj.books = articles
    sents.append(sent_obj)

result = ""
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
        result += text[startpoint:endpoint] + ' \\cite{%s}\n' % s.books[command - 1]['ID']
        db.entries.append(s.books[command - 1])
    with open('./backup.txt', 'w') as bf:
        bf.write(result)
result += text[endpoint:]
import time

for ent in db.entries:
    if 'url' in ent:
        ent['url'] = ent['url'].replace('#','')

writer = BibTexWriter()
with open('./' + time.strftime("%Y%m%d-%H%M%S") + '_bibtex.bib', 'w') as bibfile:
    bibfile.write(writer.write(db))

with open('./' + time.strftime("%Y%m%d-%H%M%S") + '_result.txt', 'w') as resultfile:
    resultfile.write(result)

# articles = scholar.main('-a="John Doe" --citation=bt')

pass

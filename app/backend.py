from datetime import date, datetime
import os
import json
import math
import urllib, urllib.request
import glob
from readabilipy import simple_json_from_html_string
import requests
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import WhitespaceTokenizer
from nltk.corpus import stopwords
from youtube_transcript_api import YouTubeTranscriptApi
import fitz
import string
import re

class Record(object):
    def __init__(self, id:str, title:str, link:str, content:str, token_frequency:dict, is_remote:bool):
        self.id = id
        self.title = title
        self.link = link
        self.content = content
        self.token_frequency = token_frequency
        self.is_remote = is_remote

    def _asdict(self):
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "content": self.content,
            "tokenFrequency": self.token_frequency,
            "is_remote": self.is_remote
        }

class Data(object):
    def __init__(self, title:str, link:str, content:str, tags:list):
        self.title = title
        self.link = link
        self.content = content
        self.tags = tags
    
    def _asdict(self):
        return {
            "title": self.title,
            "link": self.link,
            "content": self.content,
            "tags": self.tags
        }

class Payload(object):
    def __init__(self, time:int, data:list, query:list):
        self.time = time
        self.data = data
        self.query = query
    
    def _asdict(self):
        return {
            "time": self.time,
            "data": self.data,
            "query": self.query
        }

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (Data, Record, Payload)): 
            return obj._asdict()
        return json.JSONEncoder.default(self, obj)

# dict str->list(str)
global_inverted_index = {}

# dict str->list(Record)
local_record_list = {}

glob_data_path = ""
inverted_index_path = ""
local_records_path = ""
sources_path = ""

def load_index():
    global global_inverted_index
    global inverted_index_path
    if os.path.exists(inverted_index_path):
        with open(inverted_index_path, "r") as f:
            global_inverted_index = json.load(f)
    else:
        with open(inverted_index_path, "w") as f:
            json.dump({}, f)
        global_inverted_index = {}

def save_index():
    global global_inverted_index
    global inverted_index_path
    with open(inverted_index_path, "w") as f:
        json.dump(global_inverted_index, f, cls=MyEncoder)

def load_records():
    global local_records_path
    global local_record_list
    if os.path.exists(local_records_path):
        with open(local_records_path, "r") as f:
            _json = json.load(f)
            for k, j in _json.items():
                local_record_list[j["id"]] = Record(j["id"], j["title"], j["link"], j["content"], j["tokenFrequency"], j["is_remote"])
    else:
        with open(local_records_path, "w") as f:
            json.dump({}, f)
        local_record_list = {}

def save_records():
    global local_records_path
    global local_record_list
    with open(local_records_path, "w") as f:
        json.dump(local_record_list, f, cls=MyEncoder)

def initialize(data_path):
    global glob_data_path
    global inverted_index_path
    global local_records_path
    global sources_path

    glob_data_path = data_path
    inverted_index_path = os.path.join(glob_data_path, "index.json")
    local_records_path = os.path.join(glob_data_path, "local.json")
    sources_path = os.path.join(glob_data_path, "sources_count.txt")

    load_records()
    load_index()
    sync_sources()
    check_sources()


def get_sources():
    sources_dir_path = os.path.join(glob_data_path, "sources", "**/*.pdf")
    return [(os.path.split(l)[-1][:-4], l) for l in glob.iglob(sources_dir_path, recursive=True)]
    
def sync_sources():
    global local_record_list
    sources = get_sources()
    indexed_sources = [l for k, l in local_record_list.items() if not l.is_remote]
    to_scrape = []
    for title, link in sources:
        found = False
        for ind in indexed_sources:
            if title in ind.link:
                found = True
                break
        if not found:
            to_scrape.append(link)
    for ts in to_scrape:
        print("SCRAPING", ts)
        data = scrape_pdf(ts)
        key = "lc" + str(len(local_record_list))
        record = record_from_data(data, key, is_remote=False)
        local_record_list[record.id] = record
    if len(to_scrape) > 0:
        records_to_index()
        save_records()
        save_index()

def check_sources():
    global sources_path
    sources = get_sources()
    if os.path.exists(sources_path):
        with open(sources_path, "r") as f:
            count = int(f.read())
        if count != len(sources):
            with open(sources_path, "w") as f1:
                f1.write(str(count))
            sync_sources()
    else:
        with open(sources_path, "w") as f1:
            f1.write(str(len(sources)))
            sync_sources()

def add_data(data:dict):
    global local_record_list
    data = Data(data["title"], data["link"], data["content"], data["tags"])
    record = record_from_data(data, "lc" + str(len(local_record_list)), is_remote=True)
    local_record_list[record.id] = record
    records_to_index()
    save_records()
    save_index()

def records_to_index():
    global global_inverted_index
    global local_record_list
    for k, r in local_record_list.items():
        for kk, v in r.token_frequency.items():
            if kk in global_inverted_index:
                global_inverted_index[kk].append(k)
            else:
                global_inverted_index[kk] = [k]


def clean(text, as_list=False):
    txt = text.encode("ascii", "ignore").decode().lower()
    txt = txt.replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
    txt = ''.join([l for l in txt if l in set(string.ascii_letters + ' ')]).split()
    txt = [t for t in txt if len(t) > 1]
    if as_list:
        return txt
    return ' '.join(txt)

def analyze(text):
    tokens = clean(text, as_list=False)
    regex = re.compile(r'\b('+'|'.join(list(stopwords.words('english')))+r')\b', flags=re.IGNORECASE)
    tokens = regex.sub("", text).split()
    snow_stemmer = SnowballStemmer(language='english')
    return [snow_stemmer.stem(word) for word in tokens]
    
def rank(results:dict, queries:list):
    ranked_results = []
    for record_id in results:
        record = local_record_list[record_id]
        score = float(0)
        for token in queries:
            if token in record.token_frequency:
                idfval = idf(token)
                score += idfval * float(record.token_frequency[token])
        ranked_results.append({"record": record, "score": score})
    ranked_results = sorted(ranked_results, key=lambda k: k['score'], reverse=True)
    return [r["record"] for r in ranked_results]

def idf(token:str):
    return math.log10(float(len(local_record_list)) / float(len(global_inverted_index[token])))

def count_frequency(tokens:str):
    freq_words = {}
    for token in tokens:
        if token not in freq_words:
            freq_words[token] = 1
        else:
            freq_words[token] += 1
    return freq_words

def record_from_data(data, key, is_remote=True):
    tokens = analyze(data.title + data.content)
    tok_freqs = count_frequency(tokens)
    freq_to_add = len(tokens) / 5
    for meta_tag in data.tags:
        if meta_tag not in tok_freqs:
            tok_freqs[meta_tag] = freq_to_add
        else:
            tok_freqs[meta_tag] += freq_to_add
    return Record(key, data.title, data.link, data.content[:500], tok_freqs, is_remote)

def search(query):
    check_sources()
    start_time = datetime.now()
    results = {}
    queries = analyze(query)
    if len(queries) == 0:
        return Payload(0, [], [])
    temp_records = {}
    for k, q in enumerate(queries):
        if q in global_inverted_index:
            match = global_inverted_index[q]
        else:
            match = []
        for rid in match:
            temp_records[rid] = True
        keys = list(temp_records.keys())
        for record_id in keys:
            record = local_record_list[record_id]
            for qq in queries[k + 1:]:
                if (qq not in record.token_frequency) or (not record.token_frequency[qq]):
                    del temp_records[record_id]
                    break
    for record_id in temp_records:
        results[record_id] = True
    records = rank(results, queries)
    stop_time = datetime.now()
    return Payload((stop_time - start_time).microseconds / 1000, records, queries)

def scrape_yt(link:str):
    video_id = link.split("watch?v=")[1]
    srt = YouTubeTranscriptApi.get_transcript(video_id)
    if srt is None:
        return Data(None, None, None, None)
    else:
        plaintext = clean(" ".join([s["text"] + " " for s in srt]))
        url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({
            "format": "json", 
            "url": "https://www.youtube.com/watch?v=%s" % video_id
        })
        title = ""
        with urllib.request.urlopen(url) as response:
            response_text = response.read()
            try:
                data = json.loads(response_text.decode())
            except ValueError as e:
                data = None
            if data is not None:
                author = data['author_name'].split(' - ')
                author = author[0].rstrip()
                title += author + " - " + data['title']
            return Data(title, link, plaintext, [])

def scrape_pdf(link:str):
    if "file:///" in link:
        link = link[8:]
    with fitz.open(link, filetype = "pdf") as doc:
        text = ""
        for page in doc:
            text += page.getText()
        return Data(os.path.split(link)[-1][:-4], link, clean(text), [])

def scrape_link(link:str):
    req = requests.get(link)
    article = simple_json_from_html_string(req.text.encode("ascii", "ignore").decode(), use_readability=True)
    if article is not None:
        plaintext = " ".join([clean(a["text"]) + " " for a in article["plain_text"]])
        return Data(article["title"], link, plaintext, [])
    else:
        return Data(None, None, None, None)

def scrape(link:str):
    if "youtube.com" in link:
        return scrape_yt(link)
    elif link[-4:] == ".pdf":
        return scrape_pdf(link)
    else:
        return scrape_link(link)


from datetime import date, datetime
import os
import json
import math
import urllib, urllib.request
from readabilipy import simple_json_from_html_string
import nltk
import requests
from nltk.stem.snowball import SnowballStemmer
from youtube_transcript_api import YouTubeTranscriptApi
import fitz


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

# dict str->list(Record)
sources_record_list = {}

# dict str->bool
punctuation = {}

# dict str->bool
stop_words = {}

glob_data_path = ""
inverted_index_path = ""
local_records_path = ""
sources_path = ""


def load_index(path):
    global global_inverted_index
    with open(path, "r") as f:
        global_inverted_index = json.load(f)

def save_index(path):
    global global_inverted_index
    with open(path, "w") as f:
        json.dump(global_inverted_index, f, cls=MyEncoder)

def load_records(path):
    records = {}
    with open(path, "r") as f:
        _json = json.load(f)
        for k, j in _json.items():
            records[j["id"]] = Record(j["id"], j["title"], j["link"], j["content"], j["tokenFrequency"], j["is_remote"])
    return records

def save_records(path, records):
    with open(path, "w") as f:
        json.dump(records, f, cls=MyEncoder)

def initialize(data_path):
    global glob_data_path
    global inverted_index_path
    global local_records_path
    global sources_path
    global global_inverted_index
    global local_record_list
    global sources_record_list
    global punctuation
    global stop_words

    glob_data_path = data_path
    inverted_index_path = os.path.join(glob_data_path, "index.json")
    local_records_path = os.path.join(glob_data_path, "local.json")
    sources_path = os.path.join(glob_data_path, "sources.json")
    
    if not os.path.exists(inverted_index_path):
        with open(inverted_index_path, "w") as f:
            json.dump({}, f)
    
    if not os.path.exists(local_records_path):
        with open(local_records_path, "w") as f:
            json.dump({}, f)

    if not os.path.exists(sources_path):
        with open(sources_path, "w") as f:
            json.dump({}, f)

    refresh_index()

    punct = [
        ".", "?", "!", ",", ":", ";", 
        "-", "(", ")", "\"", "'", "{", 
        "}", "[", "]", "#", "<", ">", 
        "\\", "~", "*", "_", "|", "%", "/"
    ]
    stop = [
        "i", "me", "my", "myself", "we", "our",
        "ours", "ourselves", "you", "your", "'re",
        "yours", "yourself", "yourselves", "he", "him",
        "his", "himself", "she", "her", "hers", "herself",
        "it", "its", "itself", "they", "them", "their", 
        "theirs", "themselves", "what", "which", "who", 
        "whom", "this", "that", "these", "those", "am", 
        "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "having", "do", "does", "did", 
        "doing", "a", "an", "the", "and", "but", "if", "or", 
        "because", "as", "until", "while", "of", "at", "by", 
        "for", "with", "about", "against", "between", "into", 
        "through", "during", "before", "after", "above", 
        "below", "to", "from", "up", "down", "in", "out", 
        "on", "off", "over", "under", "again", "further", 
        "then", "once", "here", "there", "when", "where", 
        "why", "how", "all", "any", "both", "each", "few", 
        "more", "most", "other", "some", "such", "no", "nor", 
        "not", "'t", "'nt", "only", "own", "same", "so", 
        "than", "too", "very", "s", "t", "can", "will", 
        "just", "don", "should", "now"
    ]
    for p in punct:
        punctuation[p] = True
        
    for s in stop:
        stop_words[s] = True

import glob

def get_pdf_sources():
    sources_dir_path = os.path.join(glob_data_path, "sources", "**/*.pdf")
    local_sources = []
    for filename in glob.iglob(sources_dir_path, recursive=True):
        local_sources.append(filename)
    local_sources = [(os.path.split(l)[-1][:-4], l) for l in local_sources]
    return local_sources

def check_for_changes():
    sources_dir_path = os.path.join(glob_data_path, "sources", "**/*.pdf")
    local_sources = []
    for filename in glob.iglob(sources_dir_path, recursive=True):
        local_sources.append(filename)
    if os.path.exists(os.path.join(glob_data_path, "sources_count.txt")):
        with open(os.path.join(glob_data_path, "sources_count.txt"), "r") as f:
            count = int(f.read())
        if count != len(local_sources):
            with open(os.path.join(glob_data_path, "sources_count.txt"), "w") as f1:
                f1.write(str(count))
            refresh_index()
    else:
        with open(os.path.join(glob_data_path, "sources_count.txt"), "w") as f1:
            f1.write(str(len(local_sources)))
            refresh_index()

def sync_pdf_sources():
    global local_record_list

    sources_dir_path = os.path.join(glob_data_path, "sources", "**/*.pdf")
    local_sources = []
    for filename in glob.iglob(sources_dir_path, recursive=True):
        local_sources.append(filename)

    indexed_sources = []
    for k, l in local_record_list.items():
        if not l.is_remote:
            indexed_sources.append(l)

    to_scrape = []
    for l in local_sources:
        s = os.path.split(l)[-1]
        found = False
        for ind in indexed_sources:
            if s in ind.link:
                found = True
                break
        if not found:
            to_scrape.append(l)

    for ts in to_scrape:
        data = scrape_pdf(ts)
        key = "lc" + str(len(local_record_list))
        record = record_from_data(data, key, is_remote=False)
        local_record_list[record.id] = record

def refresh_index():
    global glob_data_path
    global inverted_index_path
    global local_records_path
    global global_inverted_index
    global local_record_list

    load_index(inverted_index_path)
    local_record_list = load_records(local_records_path)
    global_inverted_index = {}

    sync_pdf_sources()

    records_to_index(local_record_list)

    save_index(inverted_index_path)
    save_records(local_records_path, local_record_list)

def stem(tokens:list):
    new_tokens = []
    snow_stemmer = SnowballStemmer(language='english')
    for t in tokens:
        new_tokens.append(snow_stemmer.stem(t))
    return new_tokens

def tokenize(source:str):
    global punctuation
    tokens = []
    current_string = ""
    for char in source:
        ispunc = char in punctuation
        if char == " " or char == "\n":
            cur_word = current_string.lower()
            isstop = cur_word in stop_words
            if len(cur_word) != 1 and not isstop:
                tokens.append(cur_word)
            current_string = ""
        elif ispunc:
            if len(current_string) != 0 and char == "'":
                cur_word = current_string.lower()
                isstop = cur_word in stop_words
                if len(cur_word) != 1 and not isstop:
                    tokens.append(cur_word)
                current_string = ""
                current_string += "'"
            continue
        elif char.isdigit():
            continue
        else:
            current_string += char
    if len(current_string) != 0:
        cur_word = current_string.lower()
        isstop = cur_word in stop_words
        if len(cur_word) != 1 and not isstop:
            tokens.append(cur_word)
        current_string = ""
    return tokens
             
def analyze(query):
    return stem(tokenize(query))

def get_record_from_id(id):
    return local_record_list[id]

def rank(results:dict, queries:list):
    ranked_results = []
    for record_id in results:
        record = get_record_from_id(record_id)
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

def token_freq_to_index(tokens_freq:dict, unique_id:str):
    global global_inverted_index
    for k,v in tokens_freq.items():
        if k in global_inverted_index:
            global_inverted_index[k].append(unique_id)
        else:
            global_inverted_index[k] = [unique_id]

def records_to_index(records:dict):
    for k, r in records.items():
        token_freq_to_index(r.token_frequency, k)

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

def search(query, _type):
    start_time = datetime.now()
    results = {}
    queries = analyze(query)
    if len(queries) == 0:
        return Payload(0, [], [])
    if _type == "AND":
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
                record = get_record_from_id(record_id)
                for qq in queries[k + 1:]:
                    if (qq not in record.token_frequency) or (not record.token_frequency[qq]):
                        del temp_records[record_id]
                        break
        for record_id in temp_records:
            results[record_id] = True

    elif _type == "OR":
        for query in queries:
            records_with_query = global_inverted_index[query]
            for record_id in records_with_query:
                if record_id not in results:
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
        plaintext = ""
        for s in srt:
            plaintext += s["text"] + "\n"
        params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % video_id}
        url = "https://www.youtube.com/oembed"
        query_string = urllib.parse.urlencode(params)
        url = url + "?" + query_string
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
        
        return Data(os.path.split(link)[-1][:-4], link, text, [])

def scrape(link:str):
    if "youtube.com" in link:
        return scrape_yt(link)
    elif link[-4:] == ".pdf":
        return scrape_pdf(link)
    else:
        req = requests.get(link)
        article = simple_json_from_html_string(req.text.encode("ascii", "ignore").decode(), use_readability=True)
        if article is not None:
            plaintext = ""
            for a in article["plain_text"]:
                plaintext += a["text"] + "\n"
            return Data(article["title"], link, plaintext, [])
        else:
            return Data(None, None, None, None)

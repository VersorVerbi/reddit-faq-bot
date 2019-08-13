"""Adapted from Peter Norvig's spelling corrector: http://norvig.com/spell-correct.html
Original code copyright (c) 2007-2016 Peter Norvig
Used under the MIT License: https://opensource.org/licenses/mit-license.php
"""

import re
import nltk
from os.path import dirname
from collections import Counter

def words(text): return re.findall(r'\w+', text.lower())

nltk.download('words')
VOCAB = set(w.lower() for w in nltk.corpus.words.words())
ADDITIONAL_WORDS = []

WORDS = Counter(list(words(open(dirname(__file__) + '/big.txt').read())) + list(VOCAB))

def add_to_words(word):
  ADDITIONAL_WORDS.extend(word)
  return

def P(word, N=sum(WORDS.values())): return WORDS[word] / N

def correction(word): return max(candidates(word), key=P)

def candidates(word): return (known([word]) or known(edits1(word)) or known(edits2(word)) or [word])

def known(words):
  all_words = set(list(WORDS) + list(VOCAB) + ADDITIONAL_WORDS)
  return set(w for w in words if w in all_words)

def edits1(word):
  letters    = 'abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'
  splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
  deletes    = [L + R[1:]               for L, R in splits if R]
  transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
  replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
  inserts    = [L + c + R               for L, R in splits for c in letters]
  return set(deletes + transposes + replaces + inserts)

def edits2(word):
  return (e2 for e1 in edits1(word) for e2 in edits1(e1))

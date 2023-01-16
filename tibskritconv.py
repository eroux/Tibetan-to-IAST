import re
from enum import Enum
from normalize_unicode import normalize_unicode
from pathlib import Path
import logging

# ṃ ḥ ā ī ū ṛ ṝ ḷ ḹ 

ANUNASIKA_CHARACTER = "m\u0310"
ANUNASIKA_CHARACTER_2 = "m\u0301"

class Cats(Enum):
    Other = 0
    Base = 1
    Subscript = 2
    AfterVowel = 4
    Vowel = 5
    Virama = 6
    
class Special(Enum):
    No = 0
    Lengthener = 1
    R = 2
    L = 3
    I = 4
    LongI = 5


def lengthen(c):
    if c == "a":
        return "ā"
    if c == "i":
        return "ī"
    if c == "u":
        return "ū"
    return c

class State(Enum):
    Other = 0
    AfterConsonant = 1
    AfterVowel = 2
    AfterVirama = 3

class StateAutomaton():
    def __init__(self):
        self.res = ""
        self.reset()

    def reset(self):
        self.in_aksara = False
        self.lengthened = False
        self.after_r = False
        self.after_l = False
        self.vowel = None
        self.post_vowel = None
        self.state = State.Other

    def finish_aksara(self):
        if self.state == State.AfterConsonant or self.state == State.AfterVowel:
            if self.vowel is None:
                self.vowel = "a"
            if self.lengthened:
                self.vowel = lengthen(self.vowel)
            if self.after_r:
                self.res += "r"+self.vowel
            elif self.after_l:
                self.res += "l"+self.vowel
            else:
                self.res += self.vowel
            if self.post_vowel:
                self.res += self.post_vowel
                self.post_vowel = None
        self.reset()

    def get_result(self):
        self.finish_aksara()
        return self.res
        
    def update_with_token(self, t):
        (token_s, cat, special) = t
        logging.debug("new token (%s, %s, %s), state ('%s', %s, r=%s, l=%s, long=%s)", token_s, cat, special, self.res, self.state, self.after_r, self.after_l, self.lengthened)
        if cat == Cats.Base and (special == Special.L or special == Special.R):
            if self.state == State.AfterConsonant or State.AfterVowel:
                # add a
                self.finish_aksara()
        if special == Special.R:
            if self.after_l:
                self.res += "l"
                self.after_l = False
            if self.after_r:
                self.res += "r"
            self.after_r = True
            self.state = State.AfterConsonant
        elif special == Special.L:
            if self.after_r:
                self.res += "r"
                self.after_r = False
            if self.after_l:
                self.res += "l"
            self.after_l = True
            self.state = State.AfterConsonant
        elif special == Special.I or special == Special.LongI:
            if special == Special.LongI:
                self.lengthened = True
            if self.after_r:
                if self.lengthened:
                    self.vowel = "ṝ"
                else:
                    self.vowel = "ṛ"
            elif self.after_l:
                if self.lengthened:
                    self.vowel = "ḹ"
                else:
                    self.vowel = "ḷ"
            else:
                logging.warning("reverse gigu should only be after l or r")
                self.vowel = token_s
                if self.lengthened:
                    self.vowel = lengthen(self.vowel)
                self.res += self.vowel
            self.state = State.AfterVowel
            self.after_l = False
            self.after_r = False
            self.lengthened = False
        elif special == Special.Lengthener:
            # we allow achung after the vowel since it is attested in sources
            if self.vowel:
                self.vowel = lengthen(self.vowel)
            else:
                self.lengthened = True
        else:
            if cat == Cats.Vowel:
                if self.lengthened:
                    self.vowel = lengthen(token_s)
                    self.lengthened = False
                else:
                    self.vowel = token_s
                self.state = State.AfterVowel
            else:
                if self.after_r:
                    self.res += "r"
                    self.after_r = False
                if self.after_l:
                    self.res += "l"
                    self.after_l = False
            if cat == Cats.Other:
                self.finish_aksara()
                self.res += token_s
                self.state = State.Other
            if cat == Cats.Virama:
                if self.state == State.AfterVowel:
                    logging.warn("virama after a vowel")
                self.reset()
                self.state = State.AfterVirama
            if cat == Cats.AfterVowel:
                self.post_vowel = token_s
            if cat == Cats.Base:
                if self.state == State.AfterConsonant or self.state == State.AfterVowel:
                    # add a
                    self.finish_aksara()
                self.res += token_s
                self.state = State.AfterConsonant
            if cat == Cats.Subscript:
                self.res += token_s

TSEG = " "

CHAR_TOKENS = {
    "ༀ": ("oṃ", Cats.Other, 0),
    "།": ("|", Cats.Other, 0),
    "༎": ("||", Cats.Other, 0),
    "༔": ("|", Cats.Other, 0),
    "༏": ("|", Cats.Other, 0),
    "༐": ("|", Cats.Other, 0),
    "་": (TSEG, Cats.Other, 0),
    "༒": ("|", Cats.Other, 0),
    "ཀ": ("k", Cats.Base, 0),
    "ཁ": ("kh", Cats.Base, 0),
    "ག": ("g", Cats.Base, 0),
    "གྷ": ("h", Cats.Base, 0),
    "ང": ("ṅ", Cats.Base, 0),
    "ཅ": ("c", Cats.Base, 0),
    "ཆ": ("ch", Cats.Base, 0),
    "ཇ": ("j", Cats.Base, 0),
    "ཉ": ("ñ", Cats.Base, 0),
    "ཊ": ("ṭ", Cats.Base, 0),
    "ཋ": ("ṭh", Cats.Base, 0),
    "ཌ": ("ḍ", Cats.Base, 0),
    "ཌྷ": ("ḍh", Cats.Base, 0),
    "ཎ": ("ṇ", Cats.Base, 0),
    "ཏ": ("t", Cats.Base, 0),
    "ཐ": ("th", Cats.Base, 0),
    "ད": ("d", Cats.Base, 0),
    "དྷ": ("dh", Cats.Base, 0),
    "ན": ("n", Cats.Base, 0),
    "པ": ("p", Cats.Base, 0),
    "ཕ": ("ph", Cats.Base, 0),
    "བ": ("b", Cats.Base, 0),
    "བྷ": ("bh", Cats.Base, 0),
    "མ": ("m", Cats.Base, 0),
    "ཙ": ("c", Cats.Base, 0),
    "ཚ": ("ch", Cats.Base, 0),
    "ཛ": ("j", Cats.Base, 0),
    "ཛྷ": ("jh", Cats.Base, 0),
    "ཝ": ("v", Cats.Base, 0), # yes
    "ཡ": ("y", Cats.Base, 0),
    "ར": ("r", Cats.Base, Special.R),
    "ལ": ("l", Cats.Base, Special.L),
    "ཤ": ("ś", Cats.Base, 0),
    "ཥ": ("ṣ", Cats.Base, 0),
    "ས": ("s", Cats.Base, 0),
    "ཧ": ("h", Cats.Base, 0),
    "ཨ": ("", Cats.Base, 0), # should be "a", but finish_aksara() adds it already
    "ཀྵ": ("kṣ", Cats.Base, 0),
    "ཪ": ("r", Cats.Base, Special.R),
    "\u0f71": ("ā", Cats.Vowel, Special.Lengthener), # lengthener
    "\u0f72": ("i", Cats.Vowel, 0),
    "\u0f73": ("ī", Cats.Vowel, 0),
    "\u0f74": ("u", Cats.Vowel, 0),
    "\u0f75": ("ū", Cats.Vowel, 0),
    "\u0f76": ("ṛ", Cats.Vowel, 0),
    "\u0f77": ("ṝ", Cats.Vowel, 0),
    "\u0f78": ("ḷ", Cats.Vowel, 0),
    "\u0f79": ("ḹ", Cats.Vowel, 0),
    "\u0f7a": ("e", Cats.Vowel, 0),
    "\u0f7b": ("ai", Cats.Vowel, 0),
    "\u0f7c": ("o", Cats.Vowel, 0),
    "\u0f7d": ("au", Cats.Vowel, 0),
    "\u0f7e": ("ṃ", Cats.AfterVowel, 0),
    "\u0f7f": ("ḥ", Cats.AfterVowel, 0),
    "\u0f80": ("i", Cats.Vowel, Special.I),
    "\u0f81": ("ī", Cats.Vowel, Special.LongI),
    "\u0f82": (ANUNASIKA_CHARACTER_2, Cats.AfterVowel, 0),
    "\u0f83": (ANUNASIKA_CHARACTER, Cats.AfterVowel, 0),
    "\u0f84": ("-", Cats.Virama, 0), # virama
    "\u0f85": ("’", Cats.AfterVowel, 0), # avagraha
    "\u0f90": ("k", Cats.Subscript, 0),
    "\u0f91": ("kh", Cats.Subscript, 0),
    "\u0f92": ("g", Cats.Subscript, 0),
    "\u0f93": ("gh", Cats.Subscript, 0),
    "\u0f94": ("ṅ", Cats.Subscript, 0),
    "\u0f95": ("c", Cats.Subscript, 0),
    "\u0f96": ("ch", Cats.Subscript, 0),
    "\u0f97": ("j", Cats.Subscript, 0),
    "\u0f99": ("ñ", Cats.Subscript, 0),
    "\u0f9a": ("ṭ", Cats.Subscript, 0),
    "\u0f9b": ("ṭh", Cats.Subscript, 0),
    "\u0f9c": ("ḍ", Cats.Subscript, 0),
    "\u0f9d": ("ḍh", Cats.Subscript, 0),
    "\u0f9e": ("ṇ", Cats.Subscript, 0),
    "\u0f9f": ("t", Cats.Subscript, 0),
    "\u0fa0": ("th", Cats.Subscript, 0),
    "\u0fa1": ("d", Cats.Subscript, 0),
    "\u0fa2": ("dh", Cats.Subscript, 0),
    "\u0fa3": ("n", Cats.Subscript, 0),
    "\u0fa4": ("p", Cats.Subscript, 0),
    "\u0fa5": ("ph", Cats.Subscript, 0),
    "\u0fa6": ("b", Cats.Subscript, 0),
    "\u0fa7": ("bh", Cats.Subscript, 0),
    "\u0fa8": ("m", Cats.Subscript, 0),
    "\u0fa9": ("c", Cats.Subscript, 0),
    "\u0faa": ("ch", Cats.Subscript, 0),
    "\u0fab": ("j", Cats.Subscript, 0),
    "\u0fac": ("jh", Cats.Subscript, 0),
    "\u0fad": ("v", Cats.Subscript, 0), # yes
    "\u0fb1": ("y", Cats.Subscript, 0),
    "\u0fb2": ("r", Cats.Subscript, Special.R),
    "\u0fb3": ("l", Cats.Subscript, Special.L),
    "\u0fb4": ("ś", Cats.Subscript, 0),
    "\u0fb5": ("ṣ", Cats.Subscript, 0),
    "\u0fb6": ("s", Cats.Subscript, 0),
    "\u0fb7": ("h", Cats.Subscript, 0),
    "\u0fb9": ("kṣ", Cats.Subscript, 0),
    "\u0fba": ("v", Cats.Subscript, 0),
    "\u0fbb": ("y", Cats.Subscript, 0),
    "\u0fbc": ("r", Cats.Subscript, Special.R),
}

NON_SANSKRIT_CHARS = ["ཞ", "ཟ", "འ", "\u0fb8", "\u0fae", "\u0faf", "\u0fb0"]

def tibskrit_to_iast(s):
    state = StateAutomaton()
    s = normalize_unicode(s)
    for c in s:
        if c in CHAR_TOKENS:
            state.update_with_token(CHAR_TOKENS[c])
        else:
            if c in NON_SANSKRIT_CHARS:
                logging.error("%s cannot be converted to IAST", c)
                continue
            if c != "\n":
                c = ""
            state.update_with_token((c, Cats.Other, 0))
    return state.get_result()

def assert_conv(orig, expected):
    res = tibskrit_to_iast(orig)
    print(res)
    assert expected == res

def test():
    assert_conv("ཀརྨ", "karma")
    assert_conv("པདྨ", "padma")
    assert_conv("ཨཱ", "ā")
    assert_conv("མ\u0f77ཏ", "mṝta")
    assert_conv("མ\u0fb2\u0f71\u0f80ཏ", "mṝta")
    assert_conv("ག\u0f71\u0f74", "gū")
    assert_conv("ག\u0f74\u0f71", "gū")
    assert_conv("ག\u0f84མ", "gma") # virama
    assert_conv("བྷིཀྵཱུ", "bhikṣū")
    assert_conv("ཎཱཾ", "ṇāṃ")
    assert_conv("དུརྦྲྀཏྟཾ", "durbṛttaṃ")

def test_D4155():
    s = Path("D4155.txt").read_text()
    res = tibskrit_to_iast(s)
    print(res)

def shortTest():
    res = tibskrit_to_iast('།ཀརྨྨོ་པ་དེ་ཤཾ་བྷིཀྵཱུ་ཎཱཾ་སརྦྦ་ཛྙཿཀརྟྟ་མུ་ཏྱ་ཏཿ།')
    print(res)

#test()
#shortTest()
test_D4155()

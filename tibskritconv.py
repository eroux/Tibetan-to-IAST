import re
from enum import Enum
from pathlib import Path
import logging

ANUNASIKA_CHARACTER = "m\u0310"
ANUNASIKA_CHARACTER_2 = "m\u0301"

# first some Unicode normalization

class OrderCats(Enum):
    Other = 0
    Base = 1
    Subscript = 2
    BottomVowel = 3
    BottomMark = 4
    TopVowel = 5
    TopMark = 6
    RightMark = 7

CATEGORIES =  ([OrderCats.Other]           # 0F00
             + [OrderCats.Base]            # 0F01, often followed by 0f083
             + [OrderCats.Other] * 22      # 0F02-0F17
             + [OrderCats.BottomVowel] * 2 # 0F18-0F19
             + [OrderCats.Other] * 6       # 0F1A-0F1F
             + [OrderCats.Base] * 20       # 0F20-0F33, numbers can be followed by 0f18, 0f19 or exceptionally by vowels
             + [OrderCats.Other]           # 0F34
             + [OrderCats.BottomMark]      # 0F35
             + [OrderCats.Other]           # 0F36
             + [OrderCats.BottomMark]      # OF37
             + [OrderCats.Other]           # 0F38
             + [OrderCats.Subscript]       # 0F39, kind of cheating but works
             + [OrderCats.Other] * 4       # 0F3A-0F3D
             + [OrderCats.RightMark]       # 0F3E
             + [OrderCats.Other]           # 0F3F, not quite sure
             + [OrderCats.Base] * 45       # 0F40-0F6C
             + [OrderCats.Other] * 4       # 0F6D-0F70
             + [OrderCats.BottomVowel]     # 0F71
             + [OrderCats.TopVowel]        # 0F72
             + [OrderCats.TopVowel]        # 0F73
             + [OrderCats.BottomVowel] * 2 # 0F74-0F75
             + [OrderCats.TopVowel] * 8    # 0F76-0F7D
             + [OrderCats.TopMark]         # 0F7E
             + [OrderCats.RightMark]       # 0F7F
             + [OrderCats.TopVowel] * 2    # 0F80-0F81
             + [OrderCats.TopMark] * 2     # 0F82-0F83
             + [OrderCats.BottomMark]      # 0F84
             + [OrderCats.Other]           # 0F85
             + [OrderCats.TopMark] * 2     # 0F86-0F87
             + [OrderCats.Base] * 2        # 0F88-0F89
             + [OrderCats.Base]            # 0F8A always followed by 0f82 (required by the Unicode spec)
             + [OrderCats.Other]           # 0F8B
             + [OrderCats.Base]            # 0F8C
             + [OrderCats.Subscript] * 48  # 0F8D-0FBC
             )

def charcat(c):
    ''' Returns the category for a single char string'''
    o = ord(c)
    if 0x0F00 <= o <= 0x0FBC:
        return CATEGORIES[o-0x0F00]
    return OrderCats.Other

# debug:
#for i, c in enumerate(CATEGORIES):
#    print("%x : %d" % (0x0F00 + i , c.value))

def unicode_reorder(txt):
    # inpired from code for Khmer Unicode provided by SIL
    # https://docs.microsoft.com/en-us/typography/script-development/tibetan#reor
    # https://docs.microsoft.com/en-us/typography/script-development/use#glyph-reordering
    charcats = [charcat(c) for c in txt]
    # find subranges of base+non other and sort components in the subrange
    i = 0
    res = []
    valid = True
    while i < len(charcats):
        c = charcats[i]
        if c != OrderCats.Base:
            if c.value > OrderCats.Base.value:
                valid = False
            res.append(txt[i])
            i += 1
            continue
        # scan for end of component
        j = i + 1
        while j < len(charcats) and charcats[j].value > OrderCats.Base.value:
            j += 1
        # sort syllable based on character categories
        # sort the char indices by category then position in string
        newindices = sorted(range(i, j), key=lambda e:(charcats[e].value, e))
        replaces = "".join(txt[n] for n in newindices)
        res.append(replaces)
        i = j
    return "".join(res), valid

def normalize_unicode(s):
    # The code works on both NFD and NFC so there is no need to pick one or the other
    # deprecated or discouraged characters
    s = s.replace("\u0f73", "\u0f71\u0f72") # use is discouraged
    s = s.replace("\u0f75", "\u0f71\u0f74") # use is discouraged
    s = s.replace("\u0f77", "\u0fb2\u0f71\u0f80") # deprecated
    s = s.replace("\u0f79", "\u0fb3\u0f71\u0f80") # deprecated
    s = s.replace("\u0f81", "\u0f71\u0f80") # use is discouraged
    # 0f00 has not been marked as a composed character in Unicode
    # This is something that is now seen as a mistake, but it cannot be
    # changed because of Unicode change policies.
    s = s.replace("\u0f00", "\u0f68\u0f7c\u0f7e")
    # /!\ some fonts don't display these combinations in the exact same way
    # but since there's no semantic distinction and the graphical variation
    # is unclear, it seems safe
    s = s.replace("\u0f7a\u0f7a", "\u0f7b")
    s = s.replace("\u0f7c\u0f7c", "\u0f7d")
    # no 0f71 in the middle of stacks, only 0fb0
    s = re.sub(r"[\u0f71]([\u0f8d-\u0fac\u0fae\u0fb0\u0fb3-\u0fbc])", "\u0fb0\\1", s)
    # no 0fb0 at the end of stacks, only 0f71
    s = re.sub(r"[\u0fb0]([^\u0f8d-\u0fac\u0fae\u0fb0\u0fb3-\u0fbc]|$)", "\u0f71\\1", s)
    s, valid = unicode_reorder(s)
    return s


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
        return "??"
    if c == "i":
        return "??"
    if c == "u":
        return "??"
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
                    self.vowel = "???"
                else:
                    self.vowel = "???"
            elif self.after_l:
                if self.lengthened:
                    self.vowel = "???"
                else:
                    self.vowel = "???"
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
    "???": ("o???", Cats.Other, 0),
    "???": ("|", Cats.Other, 0),
    "???": ("||", Cats.Other, 0),
    "???": ("|", Cats.Other, 0),
    "???": ("|", Cats.Other, 0),
    "???": ("|", Cats.Other, 0),
    "???": (TSEG, Cats.Other, 0),
    "???": ("|", Cats.Other, 0),
    "???": ("k", Cats.Base, 0),
    "???": ("kh", Cats.Base, 0),
    "???": ("g", Cats.Base, 0),
    "???": ("h", Cats.Base, 0),
    "???": ("???", Cats.Base, 0),
    "???": ("c", Cats.Base, 0),
    "???": ("ch", Cats.Base, 0),
    "???": ("j", Cats.Base, 0),
    "???": ("??", Cats.Base, 0),
    "???": ("???", Cats.Base, 0),
    "???": ("???h", Cats.Base, 0),
    "???": ("???", Cats.Base, 0),
    "???": ("???h", Cats.Base, 0),
    "???": ("???", Cats.Base, 0),
    "???": ("t", Cats.Base, 0),
    "???": ("th", Cats.Base, 0),
    "???": ("d", Cats.Base, 0),
    "???": ("dh", Cats.Base, 0),
    "???": ("n", Cats.Base, 0),
    "???": ("p", Cats.Base, 0),
    "???": ("ph", Cats.Base, 0),
    "???": ("b", Cats.Base, 0),
    "???": ("bh", Cats.Base, 0),
    "???": ("m", Cats.Base, 0),
    "???": ("c", Cats.Base, 0),
    "???": ("ch", Cats.Base, 0),
    "???": ("j", Cats.Base, 0),
    "???": ("jh", Cats.Base, 0),
    "???": ("v", Cats.Base, 0), # yes
    "???": ("y", Cats.Base, 0),
    "???": ("r", Cats.Base, Special.R),
    "???": ("l", Cats.Base, Special.L),
    "???": ("??", Cats.Base, 0),
    "???": ("???", Cats.Base, 0),
    "???": ("s", Cats.Base, 0),
    "???": ("h", Cats.Base, 0),
    "???": ("", Cats.Base, 0), # should be "a", but finish_aksara() adds it already
    "???": ("k???", Cats.Base, 0),
    "???": ("r", Cats.Base, Special.R),
    "\u0f71": ("??", Cats.Vowel, Special.Lengthener), # lengthener
    "\u0f72": ("i", Cats.Vowel, 0),
    "\u0f73": ("??", Cats.Vowel, 0),
    "\u0f74": ("u", Cats.Vowel, 0),
    "\u0f75": ("??", Cats.Vowel, 0),
    "\u0f76": ("???", Cats.Vowel, 0),
    "\u0f77": ("???", Cats.Vowel, 0),
    "\u0f78": ("???", Cats.Vowel, 0),
    "\u0f79": ("???", Cats.Vowel, 0),
    "\u0f7a": ("e", Cats.Vowel, 0),
    "\u0f7b": ("ai", Cats.Vowel, 0),
    "\u0f7c": ("o", Cats.Vowel, 0),
    "\u0f7d": ("au", Cats.Vowel, 0),
    "\u0f7e": ("???", Cats.AfterVowel, 0),
    "\u0f7f": ("???", Cats.AfterVowel, 0),
    "\u0f80": ("i", Cats.Vowel, Special.I),
    "\u0f81": ("??", Cats.Vowel, Special.LongI),
    "\u0f82": (ANUNASIKA_CHARACTER_2, Cats.AfterVowel, 0),
    "\u0f83": (ANUNASIKA_CHARACTER, Cats.AfterVowel, 0),
    "\u0f84": ("-", Cats.Virama, 0), # virama
    "\u0f85": ("???", Cats.AfterVowel, 0), # avagraha
    "\u0f90": ("k", Cats.Subscript, 0),
    "\u0f91": ("kh", Cats.Subscript, 0),
    "\u0f92": ("g", Cats.Subscript, 0),
    "\u0f93": ("gh", Cats.Subscript, 0),
    "\u0f94": ("???", Cats.Subscript, 0),
    "\u0f95": ("c", Cats.Subscript, 0),
    "\u0f96": ("ch", Cats.Subscript, 0),
    "\u0f97": ("j", Cats.Subscript, 0),
    "\u0f99": ("??", Cats.Subscript, 0),
    "\u0f9a": ("???", Cats.Subscript, 0),
    "\u0f9b": ("???h", Cats.Subscript, 0),
    "\u0f9c": ("???", Cats.Subscript, 0),
    "\u0f9d": ("???h", Cats.Subscript, 0),
    "\u0f9e": ("???", Cats.Subscript, 0),
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
    "\u0fb4": ("??", Cats.Subscript, 0),
    "\u0fb5": ("???", Cats.Subscript, 0),
    "\u0fb6": ("s", Cats.Subscript, 0),
    "\u0fb7": ("h", Cats.Subscript, 0),
    "\u0fb9": ("k???", Cats.Subscript, 0),
    "\u0fba": ("v", Cats.Subscript, 0),
    "\u0fbb": ("y", Cats.Subscript, 0),
    "\u0fbc": ("r", Cats.Subscript, Special.R),
}

NON_SANSKRIT_CHARS = ["???", "???", "???", "\u0fb8", "\u0fae", "\u0faf", "\u0fb0"]

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
    print("%s -> %s" % (orig, res))
    assert expected == res

def test():
    assert_conv("?????????", "karma")
    assert_conv("?????????", "padma")
    assert_conv("??????", "??")
    assert_conv("???\u0f77???", "m???ta")
    assert_conv("???\u0fb2\u0f71\u0f80???", "m???ta")
    assert_conv("???\u0f71\u0f74", "g??")
    assert_conv("???\u0f74\u0f71", "g??")
    assert_conv("???\u0f84???", "gma") # virama
    assert_conv("?????????????????????", "bhik?????")
    assert_conv("?????????", "????????")
    assert_conv("???????????????????????????", "durb???tta???")

if __name__ == "__main__":
    test()
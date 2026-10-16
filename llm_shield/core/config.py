import re


_HIDDEN = re.compile("[​-‍⁠﻿‪-‮⁦-⁩]")
_NIQQUD = re.compile("[֑-ׇ]")


TOKEN_RE = re.compile(r"\[\s*([A-Z][A-Z_]*_\d+)\s*\]")
MAX_TOKEN_LEN = 40

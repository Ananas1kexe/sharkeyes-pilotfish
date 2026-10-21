import re

_HIDDEN = re.compile("[\u200b-‍⁠﻿‪-‮⁦-⁩]")
_NIQQUD = re.compile("[֑-ׇ]")


TOKEN_RE = re.compile(r"\[\s*([A-Z][A-Z_]*_\d+)\s*\]")
MAX_TOKEN_LEN = 40

_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")

_FLAGS = re.IGNORECASE | re.MULTILINE

_SECRET = (
    r"(?<![A-Za-z0-9_-])(?:"
    r"sk-ant-[A-Za-z0-9_-]{20,}"                                   # Anthropic
    r"|sk-(?:proj-)?[A-Za-z0-9_-]{20,}"                            # OpenAI
    r"|pypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,}"                     # PyPI
    r"|pypi-AgENdGVzdC5weXBpLm9yZw[A-Za-z0-9_-]{50,}"              # TestPyPI
    r"|npm_[A-Za-z0-9]{36}"                                        # npm
    r"|gh[pousr]_[A-Za-z0-9]{36,}"                                 # GitHub
    r"|github_pat_[A-Za-z0-9_]{60,}"                               # GitHub fine-grained
    r"|glpat-[A-Za-z0-9_-]{20,}"                                   # GitLab
    r"|rubygems_[a-f0-9]{48}"                                      # RubyGems
    r"|dckr_pat_[A-Za-z0-9_-]{20,}"                                # Docker Hub
    r"|(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[A-Z0-9]{16}"    # AWS key id
    r"|AIza[A-Za-z0-9_-]{35}"                                      # Google API key
    r"|ya29\.[A-Za-z0-9_-]{20,}"                                   # Google OAuth
    r"|[sr]k_(?:live|test)_[A-Za-z0-9]{24,}"                       # Stripe
    r"|xox[abposr]-[A-Za-z0-9-]{10,}"                              # Slack
    r"|hf_[A-Za-z0-9]{34,}"                                        # Hugging Face
    r"|SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}"                   # SendGrid
    r"|shp(?:at|ca|pa|ss)_[a-fA-F0-9]{32}"                         # Shopify
    r"|dop_v1_[a-f0-9]{64}"                                        # DigitalOcean
    r"|sbp_[a-f0-9]{40}"                                           # Supabase
    r"|key-[a-f0-9]{32}"                                           # Mailgun
    r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}" # JWT
    r")(?![A-Za-z0-9_-])"
)
_SLACK_WEBHOOK = r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9]{20,}"
_TELEGRAM_BOT  = r"(?<![\d:])\d{8,10}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])"
_DISCORD_BOT   = r"(?<![A-Za-z0-9_-])[MNO][A-Za-z0-9_-]{23,25}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,38}(?![A-Za-z0-9_-])"
_TWILIO        = r"(?<![A-Za-z0-9])(?:AC|SK)[0-9a-f]{32}(?![A-Za-z0-9])"
_AZURE_KEY     = r"AccountKey=([A-Za-z0-9+/]{40,}={0,2})"
_NPMRC_AUTH    = r"_authToken=([^\s]{10,})"
_AWS_SECRET    = r"(?i:aws_secret_access_key)[ \t]*[:=][ \t]*[\"']?([A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])"

_PRIVATE_KEY = r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"
_BEARER = r"(?i:\bbearer)[ \t]+([A-Za-z0-9._~+/=-]{16,})"
_CVV =  r"(?i:\b(?:cvv2?|cvc2?|cv2|security\s+code))[ \t:=#-]*(\d{3,4})(?!\d)"
_IL_PHONE = (
    r"(?<![\w+])(?:\+972|972|0)[-\s]?(?:5\d|7\d|[23489])[-\s]?\d{3}[-\s]?\d{4}(?!\d)"
)
_INTL_PHONE = r"(?<![\w+])\+\d{1,3}[\s-]?\(?\d{1,4}\)?(?:[\s-]?\d{2,4}){2,4}(?!\d)"

_EN_NAME = (
    r"(?i:\b(?:my name is|name is|call me))\s+"
    r"([A-Z][a-z'’-]+(?:\s+[A-Z][a-z'’-]+){0,2})"
)
_HE_NAME = (
    r"(?:שמי(?:\s+הוא)?|קוראים\s+לי|שם\s+מלא:?)\s+"
    r"([\u05D0-\u05EA]{2,}(?:\s+(?!ו)[\u05D0-\u05EA]{2,})?)"
)
_RU_NAME = (
    r"(?i:\b(?:меня\s+зовут|моё\s+имя|мое\s+имя))\s+"
    r"([А-ЯЁ][а-яё-]+(?:\s+[А-ЯЁ][а-яё-]+)?)"
)

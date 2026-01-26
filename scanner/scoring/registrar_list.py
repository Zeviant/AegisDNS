import re

RAW_HIGH_RISK_REGISTRARS = {
    "nicenic", "shinjiru", "jiangsu bangning", "aceville",
    "longming", "namemart", "fe-ru", "pan-asia",
    "邦宁数字技术股份有限公司", "connect electronic technology",
    "miracle ventures ltd", "naisinnike information",
    "almic ou", "openprov-ru", "hefei juming network technology co ltd",
    "成都垦派科技有限公司", "domain international services limited",
    "ultahost inc", "devexpanse regery",
    "成都伊索信息科技有限公司", "厦门纳网科技股份有限公司",
    "nawang.cn", "ALMIC OÜ",
    "nicenic.net", "nicenic.net (ZhuHai NaiSiNiKe Information Technology)",
    "NAMEMART LIMITED", "Pan-Asia Information Technology Jiangsu Co., Ltd.",
}

RAW_MEDIUM_RISK_REGISTRARS = {
    "name.com", "nets to limited", "webnic", "url solutions",
    "reg.ru", "enom", "openprovider", "onlinenic",
    "ename technology", "metaregistrar bv", "域名國際有限公司",
    "webnic.cc (web commerce communications)", "上海福虎信息科技有限公司",
    "四川域趣网络科技有限公司", "atak domain hosting", "gname",
    "南昌知乐远科技有限公司", "厦门易名科技股份有限公司",
    "mainreg inc", "河北识道网络科技有限公司",
    "dnsgulf pte ltd", "vantage of convergence chengdu technology co",
    "成都飞数科技有限公司", "netcom.cm sarl", "immaterialism limited",
    "bangning digital technology co ltd", "pdr ltd",
    "Todaynic / Eranet International"
}

RAW_LOW_RISK_REGISTRARS = {
    "namesilo", "dynadot", "west263.com", "sav.com", "tucows",
}

def normalize_registrar(name: str | None) -> str | None:
    if not name:
        return None

    # lowercasing + white spaces
    n = name.lower().strip()

    # remove punctuation
    n = re.sub(r"[.,\-/()]", " ", n)

    # remove suffixes
    n = re.sub(r"\b(inc|ltd|llc|company|co|pte)\b", "", n)

    # collapse multiple spaces into one
    n = " ".join(n.split())

    return n

HIGH_RISK_REGISTRARS = {
    normalize_registrar(r) for r in RAW_HIGH_RISK_REGISTRARS
}

MEDIUM_RISK_REGISTRARS = {
    normalize_registrar(r) for r in RAW_MEDIUM_RISK_REGISTRARS
}

LOW_RISK_REGISTRARS = {
    normalize_registrar(r) for r in RAW_LOW_RISK_REGISTRARS
}



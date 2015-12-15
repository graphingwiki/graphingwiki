from MoinMoin.parser.text_csv import Dependencies, Parser as _Parser

class Parser(_Parser):
    def __init__(self, raw, *args, **keys):
        format_args = keys.get("format_args", "")
        keys["format_args"] = 'quotechar=" ' + format_args
            
        raw = raw.rstrip()

        _Parser.__init__(self, raw, *args, **keys)

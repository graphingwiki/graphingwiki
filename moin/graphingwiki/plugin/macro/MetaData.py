Dependencies = []

def execute(macro, args):
    arglist = args.split(',')
    
    # Hidden values
    if arglist[-1] == 'hidden':
        return ''

    result = []

    if macro.formatter.in_p:
        result.append(macro.formatter.paragraph(0))

    # Failsafe for mismatched key, value pairs
    while len(arglist) > 1:
        key, val = arglist[:2]

        result.extend([macro.formatter.definition_term(1),
                       macro.formatter.text(key),
                       macro.formatter.definition_term(0),
                       macro.formatter.definition_desc(1),
                       macro.formatter.text(val),
                       macro.formatter.definition_desc(0)])

        arglist = arglist[2:]

    return u''.join(result)

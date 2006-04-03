Dependencies = []

def execute(macro, args):
    arglist = args.split(',')
    showtype = 'list'
    
    if len(arglist) % 2:
        # Hidden values
        if arglist[-1].strip() == 'hidden':
            return ''
        if arglist[-1].strip() == 'embed':
            showtype = 'raw'

    result = []

    if showtype == 'list':
        if macro.formatter.in_p:
            result.append(macro.formatter.paragraph(0))

    # Failsafe for mismatched key, value pairs
    while len(arglist) > 1:
        key, val = arglist[:2]

        if showtype == 'list':
            result.extend([macro.formatter.definition_term(1),
                           macro.formatter.text(key),
                           macro.formatter.definition_term(0),
                           macro.formatter.definition_desc(1),
                           macro.formatter.text(val),
                           macro.formatter.definition_desc(0)])
        else:
            result.extend([macro.formatter.strong(1),
                           macro.formatter.text(key),
                           macro.formatter.strong(0),
                           macro.formatter.text(val)])

        arglist = arglist[2:]

    return u''.join(result)

# -*- coding: utf-8 -*-"
"""
    CVSS base score macro plugin to MoinMoin
     - Return the value of a calculated base score.

    @copyright: 2007-2010 by Juhani Eronen <exec@iki.fi>, Lari Huttunen <debian@huttu.net>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['metadata']

from graphingwiki.editing import get_metas
from graphingwiki.util import format_wikitext, render_error

vector_keys_str = {'AV': 'AccessVector',
                   'AC': 'AccessComplexity',
                   'Au': 'Authentication',
                   'C': 'ConfImpact',
                   'I': 'IntegImpact',
                   'A': 'AvailImpact',
                   'E': 'Exploitability',
                   'RL': 'RemediationLevel',
                   'RC': 'ReportConfidence',
                   'CD': 'CollateralDamagePotential',
                   'TD': 'TargetDistribution',
                   'CR': 'SystemConfidentialityRequirement',
                   'IR': 'SystemIntegrityRequirement',
                   'AR': 'SystemAvailabilityRequirement'}

vector_str = {'AV': {'L': "Local access",
                     'A': "Adjacent network",
                     'N': "Network"},
              'AC': {'H': "High",
                     'M': "Medium",
                     'L': "Low"},
              'Au': {'N': "None required",
                     'S': "Requires single instance",
                     'M': "Requires multiple instances"},
              'C': {'N': "None",
                     'P': "Partial",
                     'C': "Complete"},
              'I': {'N': "None",
                     'P': "Partial",
                     'C': "Complete"},
              'A': {'N': "None",
                     'P': "Partial",
                     'C': "Complete"},
              'E': {'U': 'Unproven',
                    'P': 'Proof-of-concept',
                    'F': 'Functional',
                    'W': 'Widespread'},
              'RL': {'O': 'Official-fix',
                     'T': 'Temporary-fix',
                     'W': 'Workaround',
                     'U': 'Unavailable'},
              'RC': {'N': 'Not confirmed',
                     'U': 'Uncorroborated',
                     'C': 'Confirmed'},
              'CD': {'N': 'None',
                     'L': 'Low',
                     'LM': 'Low-Medium',
                     'MH': 'Medium-High',
                     'H': 'High'},
              'TD': {'N': 'None',
                     'L': 'Low',
                     'M': 'Medium',
                     'H': 'High'},
              'CR': {'L': 'Low',
                     'M': 'Medium',
                     'H': 'High'},
              'IR': {'L': 'Low',
                     'M': 'Medium',
                     'H': 'High'},
              'AR': {'L': 'Low',
                     'M': 'Medium',
                     'H': 'High'}
              }

vector_val = {'AV': {'L': 0.395,
                     'A': 0.646,
                     'N': 1.0},
              'AC': {'H': 0.35,
                     'M': 0.61,
                     'L': 0.71},
              'Au': {'N': 0.704,
                     'S': 0.56,
                     'M': 0.25},
              'C': {'N': 0.0,
                    'P': 0.275,
                    'C': 0.660},
              'I': {'N': 0.0,
                    'P': 0.275,
                    'C': 0.660},
              'A': {'N': 0.0,
                    'P': 0.275,
                    'C': 0.660},
              'E': {'U': 0.85,
                    'P': 0.9,
                    'F': 0.95,
                    'W': 1.0},
              'RL': {'O': 0.87,
                     'T': 0.9,
                     'W': 0.95,
                     'U': 1.0},
              'RC': {'N': 0.9,
                     'U': 0.95,
                     'C': 1.0},
              'CD': {'N': 0.0,
                     'L': 0.1,
                     'LM': 0.3,
                     'MH': 0.4,
                     'H': 0.5},
              'TD': {'N': 0,
                     'L': 0.25,
                     'M': 0.75,
                     'H': 1.0},
              'CR': {'L': 0.5,
                     'M': 1.0,
                     'H': 1.51},
              'IR': {'L': 0.5,
                     'M': 1.0,
                     'H': 1.51},
              'AR': {'L': 0.5,
                     'M': 1.0,
                     'H': 1.51}
              }

def parse_cvss(cvss_raw):
    cvss = dict()
    
    for asp in cvss_raw.split('/'):
        vec, val = asp.split(':')
        cvss[vec] = val

    return cvss

def cvssval(cvss, vec):
    # If it does not exist, always return 1.0 (except with CollateralDamagePotential)
    if vec == 'CD':
        val = cvss.get(vec, None)
        if not val:
            return 0.0
        return vector_val.get(vec, {}).get(val, 0.0)
    else:
        val = cvss.get(vec, None)
        if not val:
            return 1.0
        return vector_val.get(vec, {}).get(val, 1.0)

def calcimpact(impact):
    return impact == 0.0 and 0.0 or 1.176

# CVSS2
# BaseScore = round_to_1_decimal(((0.6*Impact)+(0.4*Exploitability)-1.5)*f(Impact))
# Impact = 10.41*(1-(1-ConfImpact)*(1-IntegImpact)*(1-AvailImpact))
# Exploitability = 20* AccessVector*AccessComplexity*Authentication
# f(impact)= 0 if Impact=0, 1.176 otherwise
# AccessVector     = case AccessVector of
#                         requires local access: 0.395
#                         adjacent network accessible: 0.646
#                         network accessible: 1.0
# AccessComplexity = case AccessComplexity of
#                         high: 0.35
#                         medium: 0.61
#                         low: 0.71
# Authentication   = case Authentication of
#                         requires multiple instances of authentication: 0.45
#                         requires single instance of authentication: 0.56
#                         requires no authentication: 0.704
# ConfImpact       = case ConfidentialityImpact of
#                         none:             0.0
#                         partial:          0.275
#                         complete:         0.660
# IntegImpact      = case IntegrityImpact of
#                         none:             0.0
#                         partial:          0.275
#                         complete:         0.660
# AvailImpact      = case AvailabilityImpact of
#                         none:             0.0
#                         partial:          0.275
#                         complete:         0.660

def basescore(cvss, impact=None):
    if not impact:
        impact = 10.41 * (1-(1-cvssval(cvss, 'C')) *
                            (1-cvssval(cvss, 'I')) *
                            (1-cvssval(cvss, 'A')))

    exploitability = 20 * (cvssval(cvss, 'AV') *
                           cvssval(cvss, 'AC') *
                           cvssval(cvss, 'Au'))

    base = ((0.6 * impact) + 
            (0.4 * exploitability - 1.5)) * \
            calcimpact(impact)

    return round(base, 1)

def buildVector(base_metas):
    vector = ""
    avset = set(['Local', 'Network', 'Adjacent Network'])
    acset = set(['High', 'Medium', 'Low'])
    auset = set(['Multiple', 'Single', 'None'])
    ciaset = set(['None', 'Partial', 'Complete'])
    av = base_metas["Access Vector"][:1]
    avs = set(av)
    if len(avs) > 0 and avs <= avset:
        avv = av.pop()
        vector += "AV:" + avv[0] + "/"
    else:
        return None
    ac = base_metas["Access Complexity"][:1]
    acs = set(ac)
    if len(acs) > 0 and acs <= acset:
        acv = ac.pop()
        vector += "AC:" + acv[0] + "/"
    else:
        return None
    au = base_metas["Authentication"][:1]
    aus = set(au)
    if len(aus) > 0 and aus <= auset:
        auv = au.pop()
        vector += "Au:" + auv[0] + "/"
    else:
        return None
    c = base_metas["Confidentiality"][:1]
    cs = set(c)
    if len(cs) > 0 and cs <= ciaset:
        cv = c.pop()
        vector += "C:" + cv[0] + "/"
    else:
        vector += "C:C/"
    i = base_metas["Integrity"][:1]
    ins = set(i)
    if len(ins) > 0 and ins <= ciaset:
        inv = i.pop()
        vector += "I:" + inv[0] + "/"
    else:
        vector += "I:C/"
    a = base_metas["Availability"][:1]
    avas = set(a)
    if len(avas) > 0 and avas <= ciaset:
        avav = a.pop()
        vector += "A:" + avav[0]
    else:
        vector += "A:C"
    return vector

def execute(macro, args):
    tset = set(['score', 'vector'])
    request = macro.request
    _ = request.getText

    if args:
        args = [x.strip() for x in args.split(',')]
    # Wrong number of arguments
    if len(args) not in [0,1,2]:
        return render_error(_("CVSS: Need to specify a page or page and " +
                              "type (score|vector)."))

    # Get all non-empty args
    args = [x for x in args if x]

    # If page is not specified, defaulting to current page
    if len(args) == 0:
        page = request.page.page_name
        type = "score"
    elif len(args) == 1:
        page = args[0]
        type = "score"
    else:
        page = args[0]
        type = args[1]
        if type not in tset:
            return render_error(_("CVSS: The type needs to be either score " +
                                  "or vector."))

    base_metas = get_metas(request, page, ["Access Vector", "Access Complexity", "Authentication", "Confidentiality", "Integrity", "Availability"])
    vector = buildVector(base_metas)
    if vector is not None:
        if type == "vector":
            return format_wikitext(request, vector)
        cvss = parse_cvss(vector)
        bscore = basescore(cvss)
        bstring = "%s" % bscore
        return format_wikitext(request, bstring)
    else:
        return render_error(_("CVSS: Invalid value(s) in Base Metrics."))

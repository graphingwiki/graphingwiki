import MoinMoin.wikiutil as wikiutil

from raippa import RaippaUser

def execute(pagename, request):
    course = request.form.get("course", [u''])[0]

    ruser = RaippaUser(request)
    
    draw = wikiutil.importPlugin(request.cfg, "macro", 'CourseGraph', 'draw')
    img = draw(request, course, ruser, result="img")
    request.write(img)


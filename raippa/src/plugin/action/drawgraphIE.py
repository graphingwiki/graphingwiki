import MoinMoin.wikiutil as wikiutil
from raippa.pages import Course
from raippa.user import User

def execute(pagename, request):
    type = request.form.get("type", [None])[0]
    if not type or type not in ['student', 'stats']:
        return None

    course = Course(request, request.cfg.raippa_config)

    draw = wikiutil.importPlugin(request.cfg, "macro", 'CourseGraph', 'draw_graph')
    if type == "student":
        get_data = wikiutil.importPlugin(request.cfg, "macro", 'CourseGraph', 'get_student_data')
        data = get_data(request, course, User(request, request.user.name))
    elif type == "stats":
        user = request.form.get("type", [None])[0]
        if user == "None":
            user = None
        elif user:
            user = User(request, user)

        get_data = wikiutil.importPlugin(request.cfg, "macro", 'CourseGraph', 'get_stat_data') 
        data = get_data(request, course, user)
   
    draw = wikiutil.importPlugin(request.cfg, "macro", 'CourseGraph', 'draw_graph')
    img, tag = draw(request, data, result="img")
    request.write(img)

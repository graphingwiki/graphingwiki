 # -*- coding: iso-8859-1 -*-
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter

class SlideshowException(Exception):
    def __init__(self, args=str()):
        self.args = args
    def __str__(self):
        return self.args

Dependencies = ['metadata']
generates_headings = False

def get_slides(request, pagename, slidekey, direction):
    pagedata = request.graphdata.getpage(pagename)
    slides = pagedata.get(direction, dict()).get(slidekey, list())
    
    accessible = list()
    for slide in slides:
        if Page(request, slide).exists() and request.user.may.read(slide):
            accessible.append(slide)

    return accessible

def get_slideshow(request, pagename, slidekey):
    slideshow = list()

    previous_slides = get_slides(request, pagename, slidekey, 'in')
    slide = pagename
    temp = list()

    while len(previous_slides) > 0:
        if len(previous_slides) > 1:
            raise SlideshowException(u'Multiple pages linking in to page %s.' % slide)

        slide = previous_slides.pop(0)
        if slide in temp:
            raise SlideshowException(u'Page %s is multiple times in slideshow.' % slide)
            
        temp.append(slide)
        previous_slides = get_slides(request, slide, slidekey, 'in')

    temp.reverse()
    slideshow.extend(temp)
    slideshow.append(pagename)

    next_slides = get_slides(request, pagename, slidekey, 'out')
    slide = pagename

    while len(next_slides) > 0:
        if len(next_slides) > 1:
            raise SlideshowException(u'Page %s has multiple slideshow links.' % slide)

        slide = next_slides.pop(0)
        if slide in slideshow:
            raise SlideshowException(u'Page %s is multiple times in slideshow.' % slide)
            
        slideshow.append(slide)
        next_slides = get_slides(request, slide, slidekey, 'out')

    return slideshow

def macro_MetaSlideshow(macro, slidekey=u'next'):

    request = macro.request
    formatter = macro.formatter
    pagename = macro.request.page.page_name
    page = macro.request.page

    parameters = dict()

    if request.form.get('action', [None])[0]:
        parameters['action'] = request.form['action'][0]

    if request.form.get('media', [None])[0]:
        parameters['media'] = request.form['media'][0]

    result = list()
    result.append(formatter.table(1, {"tableclass": "navigation"}))
    result.append(formatter.table_row(1))
    result.append(formatter.table_cell(1))

    if parameters.get('action', str()) == 'print':
        if parameters.get('media', str()) != 'projection':
            return None
        else:
            result.append(page.link_to(request, text='Edit ', querystr={'action':'edit'}))
            result.append(page.link_to(request, text='Wiki ', querystr=dict()))
    else:
        result.append(page.link_to(request, text='Slideshow ', querystr={'action':'print', 'media':'projection'}))
        parameters = dict()

    try:
        slideshow = get_slideshow(request, pagename, slidekey)
    except SlideshowException, e:
        return "Slideshow error: " + e.args
        

    current = slideshow.index(pagename)
    controls = ["|< ", "<< ", " >>", " >|"]
    links = dict()

    if current > 0:
        links["|< "] = slideshow[0]
        links["<< "] = slideshow[current-1]

    if current < len(slideshow)-1:
        links[" >>"] = slideshow[current+1]
        links[" >|"] = slideshow[-1]

    for index, control in enumerate(controls):
        slidepage = links.get(control, None)
        if slidepage:
            result.append(Page(request, slidepage).link_to(request, text=control, querystr=parameters))
        else:
            result.append(formatter.text(control))

        if (index == 1):
            result.append(formatter.text("Slide %i of %i" % (current+1, len(slideshow))))

    result.append(formatter.table_row(0))
    result.append(formatter.table_cell(0))
    result.append(formatter.table(0))

    return "".join(result) 

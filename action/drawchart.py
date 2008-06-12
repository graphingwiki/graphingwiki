# -*- coding: utf-8 -*-"
from pychart import *
from tempfile import mkstemp
import os 

from MoinMoin import config
from MoinMoin import wikiutil

def draw(request, data, labels, max):
    theme.output_format = "png"
    theme.use_color = 1
    theme.reinitialize()

    ar = area.T(y_range=(0,max),
                size=(750, 250),
                x_coord=category_coord.T(data, 0),
                y_axis = axis.Y(label=None),
                x_axis = axis.X(label=None))

    for index in range(len(data[0])-1):
        
        ar.add_plot(bar_plot.T(label="/14"+labels[index],
                               width=20,
                               cluster = (index,len(data[0])-1),
                               data = data,
                               hcol=index+1))

    tmp_fileno, tmp_name = mkstemp()
    can = canvas.init(tmp_name)
    ar.draw(can)
    can.close()

    fd = open(tmp_name)
    data = fd.read()
    fd.close()
    os.remove(tmp_name)

    request.write(data)

def execute(pagename, request):
#?action=drawchart&labels=users,average&start=0,1&Q1=2,3&Q2=3,5&groups=start,Q1,Q2
    max = 2
    data = request.form["groups"][0].rstrip(",").split(",")
    for key in request.form:
        if key in data:
            temp = ["/14%s" % key]
            bars = request.form[key][0].rstrip(",").split(",")
            for index, value in enumerate(bars):
                bars[index] = int(value)
                if int(value) > max:
                    max = int(value)
            temp.extend(bars)
            data[data.index(key)] = temp

    labels = request.form["labels"][0].split(",")

    draw(request, data, labels, max)

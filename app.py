from flask import Flask, render_template, url_for, request, redirect, flash
from werkzeug import secure_filename
from fitparse import FitFile
import pandas as pd
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.util.string import encode_utf8
from bokeh.models import GMapPlot, GMapOptions, ColumnDataSource, Circle, Range1d, PanTool, WheelZoomTool, ResetTool, SaveTool


app = Flask(__name__)

app.secret_key = 'fkfkjfugyujkghjogh'

ALLOWED_EXTENSIONS = set(['fit'])

####################################################################################################################
# home page
@app.route("/")
def index():
    return render_template('index.html')

# check if an extension is valid
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# upload the file, redirect user to the URL for the uploaded file:
@app.route("/analyzed", methods=['GET', 'POST'])
def analyze():
    if request.method == 'GET':
        filename = '2363427903.fit'
        fitfile = FitFile('static/2363427903.fit')
            
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(url_for('index'))
        
        file = request.files['file']
        filename = secure_filename(file.filename)
        
        # check if user does not select file
        if file.filename == '':
            flash('No selected file, please try again')
            return redirect(url_for('index'))
        
        # check if user selects wrong type of file
        if not allowed_file(file.filename):
            flash('At this time, only .fit files are accepted. Please try again')
            return redirect(url_for('index'))
        
        if file and allowed_file(file.filename):
            fitfile = FitFile(file)
###############  Sample Data  ##################################################
    gathered_names = []
    dct = {}
    frames = []
    for i in xrange(len(fitfile.messages)):
        if fitfile.messages[i].name not in gathered_names:
            gathered_names.append(fitfile.messages[i].name)
            dct = fitfile.messages[i].get_values()
            frames.append(pd.DataFrame.from_dict(dct, orient = 'index'))

    dfsampledata = pd.concat(frames, keys=gathered_names)
    dfsampledata.columns= ["Data Available (if multiple entries, only the 1st is shown)"]
            
###############  CLEAN Data for plotting  #################################################
    def deg(s):
        return s*(180./(2**31))
    
    d = []  # initialize dict
    r = 0   # initialize record counter

    # Get all data messages that are of type record
    for record in fitfile.get_messages('record'):
        r += 1

        # Go through all the data entries in this record
        for record_data in record:
            if record_data.name in ['position_lat','position_long']:
                d.append((r, record_data.name, deg(record_data.value), 'deg'))   
            else:
                d.append((r, record_data.name, record_data.value, record_data.units))

    df = pd.DataFrame(d, columns=('record','name', 'value','units'))
    dfmini = df[df['record']==1]

    cadence = df[df['name'].str.match('cadence')].reset_index().filter(regex='value').rename(columns={'value':'cadence'})
    altitude = df[df['name'].str.match('altitude')].reset_index().filter(regex='value').rename(columns={'value':'altitude'})
    distance = df[df['name'].str.match('distance')].reset_index().filter(regex='value').rename(columns={'value':'distance'})
    speed = df[df['name'].str.match('speed')].reset_index().filter(regex='value').rename(columns={'value':'speed'})
    lats = df[df['name'].str.match('position_lat')].reset_index().filter(regex='value').rename(columns={'value':'lat'})
    lons = df[df['name'].str.match('position_long')].reset_index().filter(regex='value').rename(columns={'value':'lon'})
    locs = pd.concat([lats, lons], axis=1)
####  PLOTS  ####################################################################################################
        
    plot1 = figure(plot_height=200, tools="pan, wheel_zoom,reset", title="Cadence (left foot strikes/min)")
    plot1.line(x = distance['distance']/1609.34, y=cadence['cadence'])
    
    plot2 = figure(plot_height=200, tools="pan, wheel_zoom,reset", title="Altitude (ft)")
    plot2.line(x = distance['distance']/1609.34, y=altitude['altitude']*3.28084)
    
    plot3 = figure(plot_height=200, tools="pan, wheel_zoom,reset", title="Speed (mph)")
    plot3.line(x = distance['distance']/1609.34, y=speed['speed']*2.23694)
            
####  MAP  ####################################################################################################
    
    map_options = GMapOptions(lat=locs.iloc[0][0], lng=locs.iloc[0][1], map_type="roadmap", zoom=11)
    activitymap = GMapPlot(x_range=Range1d(), y_range=Range1d(), map_options=map_options)
    activitymap.api_key = "AIzaSyBcIU6DrIyKGVxKJHbL8lgm0YMyj7UEAvU"
    source = ColumnDataSource(data=locs)
    circle = Circle(x="lon", y="lat", size=3, fill_color="blue", fill_alpha=0.9, line_color=None)
    activitymap.add_glyph(source, circle)
    activitymap.add_tools(PanTool(), WheelZoomTool(), ResetTool())
    
        
    script, div = components((activitymap, plot1, plot2, plot3))
    
    html = render_template('analyzed.html',
                           tables = [dfsampledata.to_html(), dfmini.to_html(), locs.head().to_html()],
                           titles = ['record', 'name','value','units'],
                           script = script,
                           activitymap_div = div[0],
                           plot1_div = div[1],
                           plot2_div = div[2],
                           plot3_div = div[3],
                          )
    
    return encode_utf8(html)

# **********************************
# run the app.
if __name__ == '__main__':
    app.debug = False
    app.run()
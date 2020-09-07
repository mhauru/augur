import base64
import sqlalchemy as s
import pandas as pd
import json
from flask import Response, request

#import visualization libraries
from bokeh.io import output_notebook, show, output_file
from bokeh.io.export import get_screenshot_as_png
from bokeh.plotting import figure
from bokeh.models import Label, LabelSet, ColumnDataSource, Legend
from bokeh.palettes import Colorblind
from bokeh.layouts import gridplot
from bokeh.transform import cumsum

from math import pi

from augur.routes.new_contributor_query import *

def create_routes(server):

    def vertical_bar_chart(repo_id, start_date, end_date, group_by, y_axis='new_contributors', title = "{}: {} {} Time Contributors Per {}", required_contributions = 4, required_time = 5):

        input_df = new_contributor_data_collection(repo_id=25158, num_contributions_required= required_contributions)
        months_df = months_df_query(begin_date=start_date, end_date=end_date)

        repo_dict = {repo_id : input_df.loc[input_df['repo_id'] == repo_id].iloc[0]['repo_name']}    


        contributor_types = ['All', 'repeat', 'drive_by']
        ranks = [1,2]

        row_1 = []
        row_2 = []
        row_3 = []
        row_4 = []

        for rank in ranks:
            for contributor_type in contributor_types:
                #do not display these visualizations since drive-by's do not have second contributions, and the second contribution of a repeat contributor is the same thing as the all the second time contributors
                if (rank == 2 and contributor_type == 'drive_by') or (rank == 2 and contributor_type == 'repeat'):
                    continue

                #create a copy of contributor dataframe
                driver_df = input_df.copy()
                            
                #remove first time contributors before begin date, along with their second contribution
                mask = (driver_df['yearmonth'] < start_date)
                driver_df= driver_df[~driver_df['cntrb_id'].isin(driver_df.loc[mask]['cntrb_id'])]
                
                
                #create separate repeat_df that includes all repeat contributors
                #then any contributor that is not in the repeat_df is a drive-by contributor
                repeats_df = driver_df.copy()
                
                #discards rows other than the first and the row required to be a repeat contributor
                repeats_df = repeats_df.loc[repeats_df['rank'].isin([1,required_contributions])]

                #removes all the contributors that only have a first contirbution
                repeats_df = repeats_df[repeats_df['cntrb_id'].isin(repeats_df.loc[driver_df['rank'] == required_contributions]['cntrb_id'])]
                
                #create lists of 'created_at' times for the final required contribution and the first contribution
                repeat_list = repeats_df.loc[driver_df['rank'] == required_contributions]['created_at'].tolist()
                first_list = repeats_df.loc[driver_df['rank'] == 1]['created_at'].tolist()
             
                #only keep first time contributions, since those are the dates needed for visualization
                repeats_df = repeats_df.loc[driver_df['rank'] == 1]

                #create list of time differences between the final required contribution and the first contribution, and add it to the df
                differences = []
                for i in range(0, len(repeat_list)):
                    time_difference = repeat_list[i] - first_list[i]
                    total = time_difference.days * 86400 + time_difference.seconds
                    differences.append(total)
                repeats_df['differences'] = differences

                #remove contributions who made enough contributions, but not in a short enough time
                repeats_df = repeats_df.loc[repeats_df['differences'] <= required_time * 86400]
                
                
                
                if contributor_type == 'repeat':
                    driver_df = repeats_df
                    
                    caption = """This graph shows repeat contributors in the specified time period. Repeat contributors are contributors who have 
                    made {} or more contributions in {} days and their first contribution is in the specified time period. New contributors 
                    are individuals who make their first contribution in the specified time period."""
                    
                elif contributor_type == 'drive_by':

                    #create list of 'cntrb_ids' for repeat contributors
                    repeat_cntrb_ids = repeats_df['cntrb_id'].to_list()

                    #create df with all contributors other than the ones in the repeats_df
                    driver_df = driver_df.loc[~driver_df['cntrb_id'].isin(repeat_cntrb_ids)]
                 
                    #filter df so it only includes the first contribution
                    driver_df = driver_df.loc[driver_df['rank'] == 1]
                    
                    caption = """This graph shows drive by contributors in the specified time period. Drive by contributors are contributors who 
                    make less than the required {} contributions in {} days. New contributors are individuals who make their first contribution 
                    in the specified time period. Of course, then, “All drive-by’s are by definition first time contributors”. However, not all 
                    first time contributors are drive-by’s."""
                
                
                elif contributor_type == 'All':
                    if rank == 1:
                        #makes df with all first time contributors
                        driver_df = driver_df.loc[driver_df['rank'] == 1]
                        caption = """This graph shows all the first time contributors, whether they contribute once, or contribute multiple times. 
                        New contributors are individuals who make their first contribution in the specified time period."""
                        
                    if rank == 2:
                        #creates df with all second time contributors
                        driver_df = driver_df.loc[driver_df['rank'] == 2]
                        caption = """This graph shows the second contribution of all first time contributors in the specified time period."""
                        y_axis_label = 'Second Time Contributors'
                


                #filter by end_date, this is not done with the begin date filtering because a repeat contributor will look like drive-by if the second contribution is removed by end_date filtering
                mask = (driver_df['yearmonth'] < end_date)
                driver_df = driver_df.loc[mask]

                #adds all months to driver_df so the lists of dates will include all months and years    
                driver_df = pd.concat([driver_df, months_df])

                data = pd.DataFrame()
                if group_by == 'year': 

                    data['dates'] = driver_df[group_by].unique()

                    #new contributor counts for y-axis
                    data['new_contributor_counts'] = driver_df.groupby([group_by]).sum().reset_index()[y_axis]

                    #used to format x-axis and title
                    group_by_format_string = "Year"

                elif group_by == 'quarter' or group_by == 'month':
                    
                    #set variables to group the data by quarter or month
                    if group_by == 'quarter':
                        date_column = 'quarter'
                        group_by_format_string = "Quarter"
                        
                    elif group_by == 'month':
                        date_column = 'yearmonth'
                        group_by_format_string = "Month"
                        
                    #modifies the driver_df[date_column] to be a string with year and month, then finds all the unique values   
                    data['dates'] = np.unique(np.datetime_as_string(driver_df[date_column], unit = 'M'))
                    
                    #new contributor counts for y-axis
                    data['new_contributor_counts'] = driver_df.groupby([date_column]).sum().reset_index()[y_axis]
                
                #if the data set is large enough it will dynamically assign the width, if the data set is too small it will by default set to 870 pixel so the title fits
                if len(data['new_contributor_counts']) >= 15:
                    plot_width = 46 * len(data['new_contributor_counts'])
                else:
                    plot_width = 870
                    
                #create a dict convert an integer number into a word
                #used to turn the rank into a word, so it is nicely displayed in the title
                numbers = ['Zero', 'First', 'Second']
                num_conversion_dict = {}
                for i in range(1, len(numbers)):
                    num_conversion_dict[i] = numbers[i]
                number =  '{}'.format(num_conversion_dict[rank])

                #define pot for bar chart
                p = figure(x_range=data['dates'], plot_height=400, plot_width = plot_width, title=title.format(repo_dict[repo_id], contributor_type.capitalize(), number, group_by_format_string), 
                           y_range=(0, max(data['new_contributor_counts'])* 1.15), margin = (0, 0, 10, 0))
                
                p.vbar(x=data['dates'], top=data['new_contributor_counts'], width=0.8)

                source = ColumnDataSource(data=dict(dates=data['dates'], new_contributor_counts=data['new_contributor_counts']))
                
                #add contributor_count labels to chart
                p.add_layout(LabelSet(x='dates', y='new_contributor_counts', text='new_contributor_counts', y_offset=4,
                          text_font_size="13pt", text_color="black",
                          source=source, text_align='center'))

                p.xgrid.grid_line_color = None
                p.y_range.start = 0
                p.axis.minor_tick_line_color = None
                p.outline_line_color = None

                p.title.align = "center"
                p.title.text_font_size = "18px"

                p.yaxis.axis_label = 'Second Time Contributors' if rank == 2 else 'New Contributors'
                p.xaxis.axis_label = group_by_format_string 

                p.xaxis.axis_label_text_font_size = "18px"
                p.yaxis.axis_label_text_font_size = "16px"

                p.xaxis.major_label_text_font_size = "16px"
                p.xaxis.major_label_orientation = 45.0

                p.yaxis.major_label_text_font_size = "16px"

                plot = p
                
                #creates plot to hold caption 
                p = figure(width = plot_width, height=200, margin = (0, 0, 0, 0))

                p.add_layout(Label(
                x = 0, # Change to shift caption left or right
                y = 160, 
                x_units = 'screen',
                y_units = 'screen',
                text='{}'.format(caption.format(required_contributions, required_time)),
                text_font = 'times', # Use same font as paper
                text_font_size = '15pt',
                render_mode='css'
                ))
                p.outline_line_color = None

                caption_plot = p

                if rank == 1 and (contributor_type == 'All'  or contributor_type == 'repeat'):
                    row_1.append(plot)
                    row_2.append(caption_plot)
                elif rank == 2 or contributor_type == 'drive_by':
                    row_3.append(plot)
                    row_4.append(caption_plot)

        #puts plots together into a grid
        grid = gridplot([row_1, row_2, row_3, row_4])

        return grid

    @server.app.route('/{}/reports/new_contributors/'.format(server.api_version), methods=["POST"])
    def new_contributors_report():
        #type = request.headers.get_header('application/json')

        repo_id = request.json['repo_id']
        start_date = request.json['start_date']
        end_date = request.json['end_date']
        group_by = request.json['group_by']
        required_contributions = request.json['required_contributions']
        required_time = request.json['required_time']

        #grid = vertical_bar_chart(repo_id=repo_id, start_date=start_date, end_date=end_date, group_by=group_by, required_contributions=required_contributions, required_time=required_time)
        
        #image = get_screenshot_as_png(grid, height=500, width=500, driver=webdriver)

        #return json.dumps(json_item(grid, "myplot"))


        #return send_file(image, mimetype='application/json')

        # set return headers
        #return Response(response=image,
        #                mimecode='image/png',
        #                statuscode=200)
        #return json.dumps(json_item(p, "myplot"))

        status = {
                'status': 'OK',
            }
        return Response(response=json.dumps(status),
                        status=200,
                        mimetype="application/json")

    


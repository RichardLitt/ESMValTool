"""
ESMValTool diagnostic for GLOBMAP LAI 4GST.

xxxxxxxxxxxxx add text here
"""

import datetime
import logging
import numpy as np
from scipy.stats import linregress

import iris
import iris.coord_categorisation as icc
#  import iris.quickplot as qplt
import iris.plot as iplt

import matplotlib.pyplot as plt
#  from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from matplotlib.patches import Patch

from esmvaltool.diag_scripts.shared import (
    #  ProvenanceLogger,
    get_plot_filename,
    group_metadata,
    run_diagnostic,
)

logger = logging.getLogger(__name__)

ARGMAX = iris.analysis.Aggregator("argmax",
                                  np.argmax,
                                  units_func=lambda units: 1)

# [regression pattern], id number
grow_season_types = {'EVG': [[0, 0, 0, 0], 0],
                     'TGS': [[1, -1, 1, -1], 1],
                     'SGS-S': [[1, 1, -1, -1], 2],
                     'SGS-D': [[-1, -1, 1, 1], 3],
                     }
# EVG is defined differently hence 0 0 0 0 placeholder

fig_fontsizes = {'title': 30,
                 'labels': 24,
                 'ticks': 20,
                 }

# https://davidmathlogic.com/colorblind 'Wong' colour map
# from https://www.nature.com/articles/nmeth.1618
colour_list = ['#000000', '#E69F00', '#56B4E9', '#009E73',
               '#F0E442', '#0072B2', '#D55E00', '#CC79A7'
               ]


def _get_input_cubes(metadata):
    """Load the data files into cubes.

    Inputs:
    metadata = List of dictionaries made from the preprocessor config

    Outputs:
    inputs = Dictionary of cubes
    ancestors = Dictionary of filename information
    """
    inputs = {}
    ancestors = {}
    for attributes in metadata:
        short_name = attributes['short_name']
        filename = attributes['filename']
        logger.info("Loading variable %s", short_name)
        cube = iris.load_cube(filename)
        cube.attributes.clear()
        inputs[short_name] = cube
        ancestors[short_name] = [filename]

    return inputs, ancestors


def _get_provenance_record(attributes, ancestor_files):
    """Create the provenance record dictionary.

    xxxxxxxxxxxxxxxxxx update this to GLOBMAP LAI stuff
    Inputs:
    attributes = xxxxxxx
    ancestor_files = list of data files used by the diagnostic.

    Outputs:
    record = dictionary of provenance records.
    """
    caption = "xxxxxxx do this"

    record = {
        'caption': caption,
        'statistics': ['mean', 'stddev'],  # this will need changing
        'domains': ['reg'],
        'plot_types': ['times'],
        'authors': ['king_robert'],
        #  'references': [],
        'ancestors': ancestor_files
    }

    return record


def calc_4gst(obs_mean):
    """
    Calculate the growing season type.

    Uses the method of Peano to calcuate which of the four growing
    season types each year is based on the LAI data.

    Inputs:
    obs_mean = cube of area mean of LAI timeseries

    Outputs:
    output = 2D array of years & GSTs [[year1, year2, ...], [gst1, gst2, ...]]
    """

    list_of_years = obs_mean.coord('year').points
    list_of_times = obs_mean.coord('time').points
    #  use this to be able to index the whole timeseries

    times_of_year_max = obs_mean.aggregated_by('year', iris.analysis.MAX)

    output = []
    for i, this_year in enumerate(np.unique(list_of_years)):
        if i == 0:
            continue
        # this skips the first year as we dont have lai data
        # from before to shift

        central_time = times_of_year_max[i].coord('time').points[0]

        # check if need to add extra days to the 182 to make sure
        early = central_time - 182
        late = central_time + 182

        point_list_1 = np.where(list_of_times < late)[0]
        point_list_2 = np.where(list_of_times > early)[0]
        wanted = np.intersect1d(point_list_1, point_list_2)

        obs_wanted = obs_mean[wanted]
        this_year_points = obs_wanted.coord('time').points

        this_regress = []

        # check for EVG first
        evgt = ((np.max(obs_wanted.data) - np.min(obs_wanted.data)) / 
               np.mean(obs_wanted.data))
        if evgt < 0.25:  # threshold from Peano's paper
            output.append([this_year, grow_season_types['EVG'][1]])
            continue

        for j in range(4):

            this_quarter_1 = np.where(this_year_points >= this_year_points[0] +
                                      j * 92)
            this_quarter_2 = np.where(this_year_points <= this_year_points[0] +
                                      (j + 1) * 92)

            quarter_points = np.intersect1d(this_quarter_1, this_quarter_2)

            data = obs_wanted[quarter_points].data
            days = obs_wanted[quarter_points].coord('day_of_year').points

            regress = linregress(days, data)

            this_regress.append(np.sign(regress.slope))

        for item in grow_season_types.keys():
            if this_regress == grow_season_types[item][0]:
                output.append([this_year, grow_season_types[item][1]])

    output = np.array(output).transpose()

    return output


def plot_lai_gst(obs_data, gst_data):
    """
    Take the LAI data and plot with the coloured 4GST.

    Creates a plot of the whole LAI timeseries.
    The background shading for each year represents the growing season type.

    Inputs:
    obs_data = cube of the LAI timeseries
    gst_data = array of years and GWT numbers
    """
    list_of_years = obs_data.coord('year').points

    fig = plt.figure(figsize=[30, 20], dpi=200)
    ax = fig.add_subplot(111)

    iplt.plot(obs_data,
              linewidth=3,
              color='black',
              )

    for this_year in np.unique(list_of_years):
        if this_year in gst_data[0]:
            # we have a GST
            colour_index = gst_data[1][np.where(gst_data[0] == this_year)[0][0]
                                       ]
        else:
            # no GST was able to be computed, no reason given
            colour_index = 4

        start = datetime.datetime(this_year, 1, 1)
        end = datetime.datetime(this_year + 1, 1, 1)

        plt.fill_between([start, end], [500, 500],
                         color=colour_list[3 + colour_index],
                         # want to use the last 5 colours in the list
                         alpha=0.4
                         )

    ax.xaxis.set_major_locator(mdates.YearLocator(base=1))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=6))

    ax.yaxis.set_ticks(range(0, 501, 50))

    ax.tick_params(axis='both',
                   which='major',
                   labelsize=fig_fontsizes['ticks'],
                   rotation=45)

    ax.set_xlim((datetime.datetime(list_of_years[0], 1, 1),
                 datetime.datetime(list_of_years[-1] + 1, 1, 1)
                 ))

    ax.grid(linestyle='--', linewidth=2, color='black')

    ax.set_xlabel('Date', fontsize=fig_fontsizes['labels'])
    ax.set_ylabel('LAI', fontsize=fig_fontsizes['labels'])

    fig.suptitle('LAI and 4GST', fontsize=fig_fontsizes['title'])

    legend_elements = [Patch(facecolor=colour_list[3 + 0], edgecolor='black',
                             label='EVG', alpha=0.4),
                       Patch(facecolor=colour_list[3 + 1], edgecolor='black',
                             label='TGS', alpha=0.4),
                       Patch(facecolor=colour_list[3 + 2], edgecolor='black',
                             label='SGS-S', alpha=0.4),
                       Patch(facecolor=colour_list[3 + 3], edgecolor='black',
                             label='SGS-D', alpha=0.4),
                       Patch(facecolor=colour_list[3 + 4], edgecolor='black',
                             label='Undef', alpha=0.4),
                       ]

    ax.legend(handles=legend_elements,
              bbox_to_anchor=(1.01, 1),
              prop={'size': fig_fontsizes['labels']}
              )

    plt.savefig(f'lai.png')
    plt.close()


def _diagnostic(config):
    """Perform the .......

    Parameters
    ----------
    config: dict
        the preprocessor nested dictionary holding
        all the needed information.

    Returns
    -------
    xxxxxxxxxxxxxxxxxxxxxxxx
    """
    # this loading function is based on the hydrology diagnostic
    input_metadata = config['input_data'].values()

    loaded_data = {}
    ancestor_list = []  # what is this actually used for?
    for dataset, metadata in group_metadata(input_metadata, 'dataset').items():
        cubes, ancestors = _get_input_cubes(metadata)
        loaded_data[dataset] = cubes
        # ancestor_list.append(ancestors['ts'][0])

    print(loaded_data)
    # OBS loaded_data['GLOBMAP_LAI']['lairpk']

    # note LST data needed some time coords changing
    # CMIP data had 360 day calendar, CCI data has 365 day calendar

    # obs lai, becareful with hard coded names here!!!11
    obs_lai = loaded_data['GLOBMAP_LAI']['lairpk']
    icc.add_day_of_year(obs_lai, 'time')
    icc.add_year(obs_lai, 'time')
    obs_lai_mean = obs_lai.collapsed(['latitude', 'longitude'],
                                     iris.analysis.MEAN)

    gst = calc_4gst(obs_lai_mean)
    plot_lai_gst(obs_lai_mean, gst)

    # Provenance
    # Get this information form the data cubes
    # add this back in using LST diagnostic as template


if __name__ == '__main__':
    # always use run_diagnostic() to get the config (the preprocessor
    # nested dictionary holding all the needed information)
    with run_diagnostic() as config:
        _diagnostic(config)

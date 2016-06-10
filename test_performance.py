#
# Author: Steven Blair, steven.m.blair@strath.ac.uk
#

import calendar
import datetime
import tables
import ujson
import numpy as np

import pandas as pd
from collections import OrderedDict
import time
import timeit


files = [
    'monitoring-data-float32-lz4.h5',
    'monitoring-data-float32-no-compression.h5',
    'monitoring-data-float64-lz4.h5'
]


def open_file(filename, in_memory=False):
    if in_memory:
        h5file = tables.open_file(filename, driver="H5FD_CORE", driver_core_backing_store=0)
    else:
        h5file = tables.open_file(filename)
    return h5file



def query_file(filename, in_memory=False):
    h5file = open_file(filename, in_memory=in_memory)
    monitor_tables = h5file.root

    # get all columns and first table
    all_tables = []
    all_columns = []
    for node in monitor_tables:
        table = node._f_get_child('readout')
        all_tables.append(table)
        if len(all_columns) == 0:
            all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]

    t0 = time.clock()

    # for table in all_tables:
    for i in range(0, 2):#len(all_tables)):
        table = all_tables[i]
        print '  ', table._v_parent._v_title
        values = []
        # query all columns, with date column
        for i in range(1, len(all_columns)):
            values = [[row['date'], row[all_columns[i]]] for row in table]

    t1 = time.clock()

    h5file.close()

    return t1 - t0


results = []
for filename in files:
    print 'testing:', filename
    results.append({
        'filename': filename,
        'on disk': query_file(filename, in_memory=False),
        'in memory': query_file(filename, in_memory=True)
        })

for r in results:
    print '{0: <27}'.format(r['filename'].replace('monitoring-data-', '')), 'on disk {:.3f} s,'.format(r['on disk']), 'in memory: {:.3f} s'.format(r['in memory'])

# Results (1 table):
#   float32-lz4.h5              on disk 0.963 s, in memory: 0.942 s
#   float32-no-compression.h5   on disk 0.717 s, in memory: 0.671 s
#   float64-lz4.h5              on disk 1.239 s, in memory: 1.137 s

# Results (2 tables):
#   float32-lz4.h5              on disk 27.765 s, in memory: 27.119 s
#   float32-no-compression.h5   on disk 20.601 s, in memory: 19.146 s
#   float64-lz4.h5              on disk 34.487 s, in memory: 32.051 s
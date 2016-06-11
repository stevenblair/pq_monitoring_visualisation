#
# Author: Steven Blair, steven.m.blair@strath.ac.uk
#

import calendar
import datetime
import tables
import numpy as np
import shelve
import time


def get_abbreviated_name(full_name):
    return full_name.replace(' ', '').replace('(', '').replace(')', '').replace('.', '')

def get_monitor(monitor_name):
    for node in monitor_tables:
        name = get_abbreviated_name(node._v_title)
        if name == monitor_name:
            return node._f_get_child('readout')
    return None

def get_monitor_harmonics(monitor_name, harmonics_phase):
    if harmonics_phase in harmonics_tables:
        harmonics_table_root = harmonics_tables[harmonics_phase]

        for node in harmonics_table_root:
            name = get_abbreviated_name(node._v_title)
            if name == monitor_name:
                return node._f_get_child('readout')
    return None

def phasor_diff(phasor, target):
    return 180 - abs(abs(phasor - target) - 180);

def find_phase_A_index_and_offset(phasors):
    results = []
    results_phasors = []
    for p in phasors:
        results.append(phasor_diff(p, 0.0))
        results_phasors.append(p)
    for p in phasors:
        results.append(phasor_diff(p, 180.0))
        results_phasors.append(add_angle(p, 180.0))

    # return results.index(min(results)), min(results)
    min_index = results.index(min(results))

    return min_index, results_phasors[min_index]

def identify_phase(phasor):
    if phasor > 330.0 or phasor <= 30.0:
        return 'Ia'
    if phasor > 210.0 and phasor <= 270.0:
        return 'Ib'
    if phasor > 90.0 and phasor <= 150.0:
        return 'Ic'
    if phasor > 150.0 and phasor <= 210.0:
        return '-Ia'
    if phasor > 30.0 and phasor <= 90.0:
        return '-Ib'
    if phasor > 270.0 and phasor <= 330.0:
        return '-Ic'

def add_angle(a, b):
    total = a + b
    if (total >= 360.0):
        total = total - 360.0
    return total

def add_angle_rad(a, b):
    total = a + b
    if (total >= 2 * np.pi):
        total = total - (2 * np.pi)
    return total

def neg_seq_mag(a, b, c):
    b_ang_new = add_angle(b[1], 240.0)
    c_ang_new = add_angle(c[1], 120.0)

    re = a[0] * np.cos(a[1] * np.pi / 180.0) + b[0] * np.cos(b_ang_new * np.pi / 180.0) + c[0] * np.cos(c_ang_new * np.pi / 180.0)
    im = a[0] * np.sin(a[1] * np.pi / 180.0) + b[0] * np.sin(b_ang_new * np.pi / 180.0) + c[0] * np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def pos_seq_mag(a, b, c):
    b_ang_new = add_angle(b[1], 120.0)
    c_ang_new = add_angle(c[1], 240.0)

    re = a[0] * np.cos(a[1] * np.pi / 180.0) + b[0] * np.cos(b_ang_new * np.pi / 180.0) + c[0] * np.cos(c_ang_new * np.pi / 180.0)
    im = a[0] * np.sin(a[1] * np.pi / 180.0) + b[0] * np.sin(b_ang_new * np.pi / 180.0) + c[0] * np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def any_negative_phase(a, b, c):
    # a[1] between 90 and 270
    if a[1] >= 90.0 and a[1] < 270.0:
        return True

    # b[1] between 330 and 150 (wrapped around zero)
    if b[1] >= 330.0 or b[1] < 150.0:
        return True

    # c[1] between 30 and 210 (wrapped around zero)
    if c[1] >= 210.0 or c[1] < 30.0:
        return True

    return False

def any_incorrect_phase(a, b, c):
    if a[1] >= 30.0 or (a[1] >= 30.0 and a[1] < 330.0):
        return True

    if b[1] < 210.0 or b[1] >= 270.0:
        return True

    if c[1] >= 150.0 or c[1] < 90.0:
        return True

    return False

def correct_waveform_phasors(monitor_name):
    harmonics_phases = ['Ia', 'Ib', 'Ic']

    for h in harmonics_phases:
        table = get_monitor_harmonics(monitor_name, h)
        print table.nrows
    # nrows = get_monitor_harmonics(monitor_name, 'Ia').nrows
    # print nrows

    longest_table = max([get_monitor_harmonics(monitor_name, h).nrows for h in harmonics_phases])

    if longest_table > 0:
        earliest_date = min([get_monitor_harmonics(monitor_name, h)._v_parent._v_attrs.earliest_date for h in harmonics_phases])
        latest_date = max([get_monitor_harmonics(monitor_name, h)._v_parent._v_attrs.latest_date for h in harmonics_phases])
        # print longest_table, earliest_date, latest_date

        # check each 15 min interval
        for date in range(earliest_date, latest_date + 900, 900):
            phasors = []


            for h in harmonics_phases:
                table = get_monitor_harmonics(monitor_name, h)

                p = [(row['H1_mag'], row['H1_ang'] * 180.0 / (np.pi)) for row in table.where('date == ' + str(date))]
                
                if len(p) == 1:
                    phasors.append(p[0])

            # check data exists and in valid magnitude range
            if len(phasors) == 3 and all(m >= 50.0 for m in [phasors[0][0], phasors[1][0], phasors[2][0]]):
                # print 'pos seq mag:', pos_seq_mag(phasors[0], phasors[1], phasors[2])
                # print 'neg seq mag:', neg_seq_mag(phasors[0], phasors[1], phasors[2])

                # only take action if current negative sequence is greater than 50% (relative to rated current in Amperes)
                # (this will cater for wrong sequence and current polarity errors, regardless of power factor)
                if (neg_seq_mag(phasors[0], phasors[1], phasors[2]) / 5.0) > 50.0 or any_incorrect_phase(phasors[0], phasors[1], phasors[2]):
                    # print phasors
                    phase_A, offset = find_phase_A_index_and_offset([phasors[0][1], phasors[1][1], phasors[2][1]])
                    # print phase_A, offset
                    # print add_angle(phasors[0][1], offset), add_angle(phasors[1][1], offset), add_angle(phasors[2][1], offset)

                    # first find the phase closest to 0deg (or 180deg) and normalise all phasor angles
                    # print phasor_diff(phasors[0][1], 0.0), phasor_diff(phasors[1][1], 0.0), phasor_diff(phasors[2][1], 0.0)
                    # print phasor_diff(phasors[0][1], 180.0), phasor_diff(phasors[1][1], 180.0), phasor_diff(phasors[2][1], 180.0)
                    first_col = identify_phase(sub_angle(phasors[0][1], offset))
                    second_col = identify_phase(sub_angle(phasors[1][1], offset))
                    third_col = identify_phase(sub_angle(phasors[2][1], offset))
                    col_changes = [first_col, second_col, third_col]

                    if first_col == 'Ia' and second_col == 'Ib' and third_col == 'Ic':
                        # print 'correct sequence and polarity'
                        pass
                    else:
                        # print 'incorrect sequence and/or polarity'
                        indices = {}
                        original_rows = {}
                        updated_rows = {}
                        for h in harmonics_phases:
                            table = get_monitor_harmonics(monitor_name, h)
                            indices[h] = table.get_where_list('date == ' + str(date))
                            original_rows[h] = table[indices[h]]
                            # original_rows[h] = table.where('date == ' + str(date))
                            # print 'len(original_rows[h]):', len(original_rows[h])
                            # print original_rows[h]
                            # print all_cols

                        # update magnitudes and/or sequence
                        for ch, original_phase in zip(col_changes, harmonics_phases):
                            updated_rows[ch.replace('-', '')] = original_rows[original_phase]
                            if '-' in ch:
                                for j, r in enumerate(updated_rows[ch.replace('-', '')]):
                                    updated_rows[ch.replace('-', '')][j][6] = add_angle_rad(updated_rows[ch.replace('-', '')][j][6], np.pi)

                                # print 'updated to:', updated_rows[ch.replace('-', '')][0][6]
                                # print updated_rows[ch.replace('-', '')][0]
                                # for col in updated_rows[ch.replace('-', '')]:
                                #     updated_rows[ch.replace('-', '')][6] = add_angle_rad(updated_rows[ch.replace('-', '')][6], np.pi)
                                #     # print col
                                #     if 'H1_ang' in col:
                                #         print 'updating:', col, updated_rows[ch.replace('-', '')][col]
                                #         updated_rows[ch.replace('-', '')][col] = add_angle_rad(updated_rows[ch.replace('-', '')][col], np.pi)
                                #     # if 'H1_mag' in col:
                                #     #     updated_rows[original_phase][col] = updated_rows[original_phase][col] * -1.0
                                # # updated_rows[ch.replace('-', '')] = [original_rows[original_phase] * -1.0 if 'H1_mag' in col for col in original_rows[original_phase]]


                        for h in harmonics_phases:
                            table = get_monitor_harmonics(monitor_name, h)
                            # table.modify_rows(start=start, stop=stop, rows=updated_rows[h])
                            if h not in indices:
                                print 'h not in indices'
                            if h not in updated_rows:
                                print 'h not in updated_rows', col_changes

                            if h in indices and h in updated_rows:
                                table[indices[h]] = updated_rows[h]
            else:
                # print 'invalid date', len(phasors), phasors
                pass


def precalculate_monitors_list():
    if len(monitors_list) == 0:
        for node, harmonics_node in zip(monitor_tables, harmonics_tables['Va']):
            monitor_name_index = get_abbreviated_name(node._v_title)

            harmonics_earliest_date = max([harmonics_tables[f]._f_get_child(monitor_name_index)._v_attrs.earliest_date for f in harmonics_tables])
            harmonics_latest_date = min([harmonics_tables[f]._f_get_child(monitor_name_index)._v_attrs.latest_date for f in harmonics_tables])
            
            monitors_list.append({
                'monitor_name_index': monitor_name_index,
                'monitor_name': node._v_title,
                'monitor_name_formatted': node._v_attrs.secondary_name_formatted,
                'ring_ID': node._v_attrs.ring_ID,
                'primary_name': node._v_attrs.primary_name_formatted,
                'earliest_date': node._v_attrs.earliest_date,
                'latest_date': node._v_attrs.latest_date,
                'harmonics_earliest_date': harmonics_earliest_date,
                'harmonics_latest_date': harmonics_latest_date,
                'total_rows': int(node._v_attrs.total_rows),
                'total_days': int(node._v_attrs.total_days)
            })

        monitors_list.sort(key=lambda x:(x['primary_name'], x['monitor_name_formatted']))


def get_monitors_from_ring_ID(ring_ID):
    matches = []

    for m in monitors_list:
        if ring_ID == m['ring_ID']:
            matches.append(m)

    return matches

def precalculate_C2C_events():
    shelf = shelve.open('sorted_events')
    sorted_events = shelf['sorted_events']
    shelf.close()

    for m in monitors_list:
        C2C_events[m['monitor_name_index']] = {
            'NOP_opened': [],
            'NOP_closed': [],
        }

    for ring_ID, events in sorted_events.iteritems():
        monitors = get_monitors_from_ring_ID(ring_ID)
        for event in events:
            for m in monitors:
                if event[1] == 'Closed':
                    C2C_events[m['monitor_name_index']]['NOP_closed'].append({"t": int(time.mktime(event[0].timetuple()) * 1000), "duration_ms": 0.0})
                else:
                    C2C_events[m['monitor_name_index']]['NOP_opened'].append({"t": int(time.mktime(event[0].timetuple()) * 1000), "duration_ms": 0.0})


FILENAME = 'data/monitoring-data-float32-no-compression.h5'
HARMONICS_FILENAMES = {
    'Va': 'data/L1-N(V) Harmonics.h5',
    'Vb': 'data/L2-N(V) Harmonics.h5',
    'Vc': 'data/L3-N(V) Harmonics.h5',
    'Ia': 'data/L1(A) Harmonics.h5',
    'Ib': 'data/L2(A) Harmonics.h5',
    'Ic': 'data/L3(A) Harmonics.h5'
}
EVENT_FILENAME = 'data/event-data.h5'

INDIVIDUAL_HARMONICS = True
IN_MEMORY = False

monitors_list = []
daily_resampled_data = {}
heatmap_precalculated_data = {}
harmonics_tables = {}
C2C_events = {}

if __name__ == '__main__':
    # open database file
    if IN_MEMORY:
        # note that 'driver_core_backing_store=0' disables persisting changes to disk
        h5file = tables.open_file(FILENAME, driver="H5FD_CORE", driver_core_backing_store=0)
    else:
        h5file = tables.open_file(FILENAME)
    monitor_tables = h5file.root

    if INDIVIDUAL_HARMONICS:
        for f in HARMONICS_FILENAMES:
            h5file = tables.open_file(HARMONICS_FILENAMES[f], mode='a')
            harmonics_tables[f] = h5file.root

    h5file = tables.open_file(EVENT_FILENAME)
    event_tables = h5file.root

    precalculate_monitors_list()
    precalculate_C2C_events()

    for m in monitors_list:
        print m['monitor_name_index']
        correct_waveform_phasors(m['monitor_name_index'])

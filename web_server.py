#
# Author: Steven Blair, steven.m.blair@strath.ac.uk
#

import calendar
import datetime
import tables
import ujson
import numpy as np
import shelve

import pandas as pd
from collections import OrderedDict
import time

from twisted.web import server, resource
from twisted.internet import reactor#, ssl
from twisted.web.static import File


class NamedTimer():
    def __init__(self):
        self.enabled = False

        if self.enabled:
            self.things = [('start', time.clock())]

    def add(self, name):
        if self.enabled:
            self.things.append((name, time.clock()))

    def stop(self):
        if self.enabled:
            total = sum([self.things[i][1] - self.things[i - 1][1] for i, x in enumerate(self.things) if i > 0])
            for i, x in enumerate(self.things):
                if i > 0:
                    diff_time = self.things[i][1] - self.things[i - 1][1]
                    print x[0].ljust(32), '{:.3f} s,'.format(diff_time), '{:.1f}%'.format(100.0 * diff_time / total)
            print ''

def get_abbreviated_name(full_name):
    return full_name.replace(' ', '').replace('(', '').replace(')', '').replace('.', '')

def precalculate_heat_map_data():
    all_columns = []
    for node in monitor_tables:
        table = node._f_get_child('readout')
        all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]
        break

    for node in monitor_tables:
        timer = NamedTimer()
        table = node._f_get_child('readout')
        name = get_abbreviated_name(node._v_title)
        print name

        for column in all_columns[3:]:
            values = [[row['date'], row[column]] for row in table]
            timer.add('heatmap, query')

            values_dict = {}
            for v in values:
                # get mean value for each 1-hour slot
                day = datetime.datetime.utcfromtimestamp(v[0]).replace(minute=0, second=0)
                if day in values_dict:
                    values_dict[day] = (values_dict[day][0] + v[1], values_dict[day][1] + 1)
                else:
                    values_dict[day] = (v[1], 1)
            timer.add('heatmap, loop through values')

            # arrange values into list format
            values_out = []
            for key in values_dict.keys():
                values_out.append([calendar.timegm(key.timetuple()) * 1000, key.hour, values_dict[key][0] / values_dict[key][1]])

            heatmap_precalculated_data[(name, column)] = ujson.dumps(values_out)  # TODO might be more memory-efficient before JSON format?
            timer.add('heatmap, values_out')
        timer.stop()

def precalculate_daily_resampling():
    all_columns = []
    for node in monitor_tables:
        table = node._f_get_child('readout')
        all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]
        break

    for node in monitor_tables:
        timer = NamedTimer()
        table = node._f_get_child('readout')
        name = get_abbreviated_name(node._v_title)

        values = [[row[c] for c in all_columns] for row in table]
        timer.add(name + ' query table')
        # print 'length of query results:', len(values)
        
        if len(values) > 0:
            df = pd.DataFrame(values, columns=all_columns)
            timer.add(name + ' create DataFrame')

            df['date'] = pd.to_datetime(df['date'], unit='s')
            timer.add(name + ' convert timestamp to datetime')

            df.set_index('date', inplace=True)
            timer.add(name + ' set_index of DataFrame')

            df2 = df.resample('24H', how=get_resampling_type_dict(all_columns[3:]))
            timer.add(name + ' resampling DataFrame')

            df2.reset_index(inplace=True)
            timer.add(name + ' reset index')

            daily_resampled_data[name] = df2
            timer.add(name + ' store DataFrame')

        timer.stop()


def get_resampling_freq(days_delta):
    resampling_freq = '24H'
    if days_delta <= 2:
        resampling_freq = '5Min'
    elif days_delta < 5:
        resampling_freq = '10Min'
    elif days_delta < 10:
        resampling_freq = '30Min'
    elif days_delta < 20:
        resampling_freq = '1H'
    elif days_delta < 50:
        resampling_freq = '2H'
    elif days_delta < 75:
        resampling_freq = '4H'
    elif days_delta < 100:
        resampling_freq = '6H'
    elif days_delta < 160:
        resampling_freq = '8H'
    elif days_delta < 300:
        resampling_freq = '12H'
    return resampling_freq

def get_resampling_type_dict(columns):
    ret = OrderedDict()
    for col in columns:
        if 'Max' in col:
            ret[col] = 'max'
        elif 'Min' in col:
            ret[col] = 'min'
        else:
            ret[col] = 'mean'
    return ret

def get_monitor(monitor_name):
    for node in monitor_tables:
        name = get_abbreviated_name(node._v_title)
        if name == monitor_name:
            return node._f_get_child('readout')
    return None

def get_monitor_from_tables(monitor_name, tables):
    for node in tables:
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

def get_data(monitor_name, from_dt, to_dt, columns):
    timer = NamedTimer()
    # rather than blindly cutting samples using the 'step' option, fetch all data then re-sample to reduce data size
    NUMBER_OF_VALUES = 576  # 2 days

    table = get_monitor(monitor_name)

    # check for pre-resampled data
    if (calendar.timegm(from_dt.timetuple()) <= table._v_parent._v_attrs.earliest_date and calendar.timegm(to_dt.timetuple()) >= table._v_parent._v_attrs.latest_date):
        # using all pre-resampled data
        if monitor_name in daily_resampled_data:
            df = daily_resampled_data[monitor_name][columns]
            out = df.to_json(orient="values", date_format='epoch', date_unit='ms')
            # print 'using pre-resampled, number of samples:', len(df)
            return out
    elif get_resampling_freq((to_dt - from_dt).days) == '24H':
        # using a subset of pre-resampled data
        if monitor_name in daily_resampled_data:
            df = daily_resampled_data[monitor_name][columns]
            df2 = df[(df.date >= np.datetime64(from_dt)) & (df.date <= np.datetime64(to_dt))]
            out = df2.to_json(orient="values", date_format='epoch', date_unit='ms')
            # print 'using pre-resampled subset, number of samples:', len(df2)
            return out
    
    # cannot use precalculated values; query data and resample if needed
    values = [[row[c] for c in columns] for row in table.where('(date >= ' + str(calendar.timegm(from_dt.timetuple())) + ') & (date <= ' + str(calendar.timegm(to_dt.timetuple())) + ')')]
    timer.add('query rows')

    # return values, resampling if needed
    if len(values) <= NUMBER_OF_VALUES:
        # convert to JavaScript convention of datetime
        for v in values:
            v[0] = v[0] * 1000
        # print 'not resampling, number of samples:', len(values)

        timer.add('conversion to millisecond')
        timer.stop()
        return ujson.dumps(values)
    else:
        # input_dict = {t: x for t, x in zip(input_t, input_signal)}
        # df = pd.DataFrame(input_signal, index=input_t, columns=['Current_RMS_10_Cycle_Avg_A'])
        days_delta = (to_dt - from_dt).days#len(values) / (24.0 * 12.0)#
        resampling_freq = get_resampling_freq(days_delta)
        resampling_type = get_resampling_type_dict(columns[1:])

        if resampling_freq == '24H' and monitor_name in daily_resampled_data:
            # if 24H sampling required, use precalculated values
            df = daily_resampled_data[monitor_name][columns]
            df2 = df[(df.date >= np.datetime64(from_dt)) & (df.date <= np.datetime64(to_dt))]
            out = df2.to_json(orient="values", date_format='epoch', date_unit='ms')
            # print 'using pre-resampled subset, number of samples:', len(df2)
            return out
        else:
            df = pd.DataFrame(values, columns=columns)
            timer.add('create DataFrame')
            df['date'] = pd.to_datetime(df['date'], unit='s')
            timer.add('convert timestamp to datetime')
            df.set_index('date', inplace=True)
            timer.add('set_index of DataFrame')

            df2 = df.resample(resampling_freq, how=resampling_type)
            timer.add('resampling')
            # df2.fillna(0, inplace=True)

            df2.reset_index(inplace=True)
            out = df2.to_json(orient="values", date_format='epoch', date_unit='ms')
            timer.add('to JSON')
            timer.stop()

            # print 'resampling, number of samples:', len(df2), 'days_delta:', int(days_delta), 'resampling_freq', resampling_freq, "raw values", len(values)
            return out

def get_data_heat_map(monitor_name, columns):
    column = columns[1]

    if PRECALCULATE_HEATMAP_DATA and (monitor_name, column) in heatmap_precalculated_data:
        return heatmap_precalculated_data[(monitor_name, column)]
    else:
        timer = NamedTimer()

        table = get_monitor(monitor_name)
        values = [[row['date'], row[column]] for row in table]
        timer.add('heatmap, query')

        values_dict = {}
        for v in values:
            # get mean value for each 1-hour slot
            day = datetime.datetime.utcfromtimestamp(v[0]).replace(minute=0, second=0)
            if day in values_dict:
                values_dict[day] = (values_dict[day][0] + v[1], values_dict[day][1] + 1)
            else:
                values_dict[day] = (v[1], 1)
        timer.add('heatmap, loop through values')

        # arrange values into list format
        values_out = []
        for key in values_dict.keys():
            values_out.append([calendar.timegm(key.timetuple()) * 1000, key.hour, values_dict[key][0] / values_dict[key][1]])

        timer.add('heatmap, values_out')
        timer.stop()
        return ujson.dumps(values_out)


def is_pos_seq(values_rad):
    values_deg = np.rad2deg(values_rad)
    threshold = 45.0
    ret = [False, False, False]
    
    # phase A - may wrap around zero
    if ((360.0 - threshold) <= values_deg[0] <= 360) or (0.0 <= values_deg[0] <= threshold):
        ret[0] = True

    # phase B
    if ((240.0 - threshold) <= values_deg[1] <= (240 + threshold)):
        ret[1] = True

    # phase C
    if ((120.0 - threshold) <= values_deg[2] <= (120 + threshold)):
        ret[2] = True

    if all(ret):
        return True

    return False


def get_data_waveform(monitor_name, harmonics_type, from_dt):
    if INDIVIDUAL_HARMONICS:
        timer = NamedTimer()

        harmonics_phases = ['Va', 'Vb', 'Vc']
        if harmonics_type == 'current':
            harmonics_phases = ['Ia', 'Ib', 'Ic']

        waveforms = [[], [], []]
        DC = []
        mags = []
        angs = []

        for h in harmonics_phases:
            table = get_monitor_harmonics(monitor_name, h)
            all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]

            mag = [[row[c] for c in all_columns if 'mag' in c and 'inter' not in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
            ang = [[row[c] for c in all_columns if 'ang' in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
            
            if len(mag) > 0:
                DC.append(mag[0][0])
                mags.append(mag[0][1:])
                angs.append(ang[0][1:])

            timer.add('waveforms, query ' + h)

        if len(mags) > 0:
            # if red 

            phase_polarity = [1.0, 1.0, 1.0]
            change_seq = not is_pos_seq([angs[i][0] for i in range(0, 3)])

            waveform_duration = 0.04    # seconds
            F_nom = 50.0                # Hz
            steps = 400
            timestep = waveform_duration / steps

            t_values = np.linspace(0.0, waveform_duration, steps, endpoint=False)
            harmonics_numbers = np.array(range(1, 64))
            f_values = 2 * np.pi * 50.0 * harmonics_numbers

            for i in range(0, steps):
                t = i * timestep
                # loop through phase numbers, and generate waveform time series
                for n in [0, 1, 2]:
                    v = phase_polarity[n] * (DC[n] + np.sum(np.array(mags[n]) * np.sin(t * f_values + np.array(angs[n]))))
                    waveforms[n].append(v)

            if harmonics_type == 'voltage' and change_seq:
                waveforms[1], waveforms[2] = waveforms[2], waveforms[1]

            # # for manually testing output waveforms
            # for v in waveforms:
            #     print v

        timer.add('waveforms, waveforms')
        timer.stop()
        return ujson.dumps(waveforms)


def get_data_harmonics(monitor_name, harmonics_type, from_dt, show_fundamental=True, to_pu=False, interharmonics=False):
    if INDIVIDUAL_HARMONICS:
        timer = NamedTimer()

        harmonics_phases = ['Va', 'Vb', 'Vc']
        if harmonics_type == 'current':
            harmonics_phases = ['Ia', 'Ib', 'Ic']

        mags = []

        for h in harmonics_phases:
            table = get_monitor_harmonics(monitor_name, h)
            all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]

            if interharmonics:
                mag = [[row[c] for c in all_columns if 'inter_mag' in c or 'H1_mag' in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
            else:
                mag = [[row[c] for c in all_columns if 'mag' in c and 'inter' not in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
                

            if len(mag) > 0:
                fundamental_mag = mag[-1][1]
                mags.append(mag[0])
                if not show_fundamental and not interharmonics:
                    mags[-1][1] = 0.0
                if to_pu:
                    for i, v in enumerate(mags[-1]):
                        mags[-1][i] = mags[-1][i] * 100.0 / fundamental_mag

                if interharmonics:
                    mags[-1].remove(mags[-1][1])

            timer.add('harmonics, query ' + h)

        values_out = []
        if len(mags) > 0:
            # harmonic_numbers = np.arange(0, 64, step=0.5).tolist()#range(0, 64)
            # if interharmonics:
            #     harmonic_numbers = []
            #     harmonic_numbers_integer = range(0, 64)
            #     for h in harmonic_numbers_integer:
            #         # harmonic_numbers.append(str(h))
            #         harmonic_numbers.append(str(h) + ' interharmonic')
            # else:
            #     harmonic_numbers = range(0, 64)
            harmonic_numbers = range(0, 64)

            values_out = [harmonic_numbers, mags[0], mags[1], mags[2]]

        timer.add('harmonics, waveforms')
        timer.stop()
        return ujson.dumps(values_out)


def get_data_harmonic_trends(monitor_name, harmonics_type, harmonic_numbers, from_dt, to_dt, show_fundamental=False, to_pu=False):
    if INDIVIDUAL_HARMONICS:
        timer = NamedTimer()
        NUMBER_OF_VALUES = 576  # 2 days

        harmonics_phases = ['Va', 'Vb', 'Vc']
        if harmonics_type == 'current':
            harmonics_phases = ['Ia', 'Ib', 'Ic']

        harmonic_column_labels = ['date'] + ['H' + str(n) + '_mag' for n in harmonic_numbers]
        mags_sum = np.zeros(1 + len(harmonic_numbers))
        timer.add('harmonics trends, init')
        dfs = []

        for h in harmonics_phases:
            table = get_monitor_harmonics(monitor_name, h)
            mags = [[row[c] for c in harmonic_column_labels] for row in table.where('(date >= ' + str(calendar.timegm(from_dt.timetuple())) + ') & (date <= ' + str(calendar.timegm(to_dt.timetuple())) + ')')]
            if len(mags) > 0:
                df = pd.DataFrame(mags, columns=['date'] + harmonic_numbers)
                df['date'] = pd.to_datetime(df['date'], unit='s')
                df.set_index('date', inplace=True)
                dfs.append(df)
                timer.add('harmonics trends, query ' + h)

        if len(dfs) == 0:
            return '[]'

        df_concat = pd.concat(dfs)
        df_mean = df_concat.groupby(level=0).mean()

        if to_pu:
            df_mean = df_mean.div(df_mean[1], axis='index') * 100.0
        # if not show_fundamental:
        #     df_mean.drop(1, axis=1, inplace=True)
        #     harmonic_numbers.remove(1)

        # use pandas to resample, if needed
        if len(df_mean) <= NUMBER_OF_VALUES:
            df_mean.reset_index(inplace=True)
            # print 'not resampling'
            values_out = []
            for col in df_mean.columns.values:
                if col == 'date':
                    values_out.append((df_mean[col].values.astype(np.int64) // 10 ** 6).tolist())
                else:
                    values_out.append(df_mean[col].tolist())

            return ujson.dumps(values_out)
        else:
            days_delta = (to_dt - from_dt).days#len(df_mean) / (24.0 * 4.0)
            resampling_freq = get_resampling_freq(days_delta)
            resampling_type = 'mean'

            df2 = df_mean.resample(resampling_freq, how=resampling_type)
            # print 'resampling, number of samples:', len(df2), 'days_delta:', days_delta, 'resampling_freq', resampling_freq
            timer.add('harmonics trends, resampling')

            df2.replace([np.inf, -np.inf], np.nan, inplace=True)
            df2.dropna(inplace=True)
            df2.reset_index(inplace=True)

            # TODO use same approach for other plot types, rather than to_json?
            values_out = []
            for col in df2.columns.values:
                if col == 'date':
                    values_out.append((df2[col].values.astype(np.int64) // 10 ** 6).tolist())
                else:
                    values_out.append(df2[col].tolist())

            timer.add('harmonics trends, reorganise output')
            timer.stop()

            return ujson.dumps(values_out)


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


class MonitorsResource(resource.Resource):
    isLeaf = True
    
    def render_GET(self, request):
        # e.g.: http://localhost/monitors
        request.setHeader("content-type", "application/json")
        return ujson.dumps(monitors_list)


class EventsResource(resource.Resource):
    isLeaf = True
    
    def render_GET(self, request):
        # e.g.: http://localhost/events
        request.setHeader("content-type", "application/json")
        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        columns = ['date', 'Event_Type', 'duration_ms']

        values = []
        out = {}
        if monitor_name:
            table = get_monitor_from_tables(monitor_name, event_tables)
            values = [{c: row[c] for c in columns} for row in table]

            for v in values:
                if v['Event_Type'] not in out.keys():
                    out[v['Event_Type']] = [{"t": v['date'] * 1000, "duration_ms": v['duration_ms']}]
                else:
                    out[v['Event_Type']].append({"t": v['date'] * 1000, "duration_ms": v['duration_ms']})

            out['NOP_opened'] = C2C_events[monitor_name]['NOP_opened']
            out['NOP_closed'] = C2C_events[monitor_name]['NOP_closed']

        return ujson.dumps(out)

class EventWaveformResource(resource.Resource):
    isLeaf = True
    
    def render_GET(self, request):
        # e.g.: http://localhost/event/ASHTONPK171032/1372849093
        #       http://localhost/event/ONEILLS314504/1361346002
        #       http://localhost/event/THEARTHS167632/1361793957
        #       http://localhost/event/ASHTONPK171032/1396195657
        request.setHeader("content-type", "application/json")
        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        date = uri_parts[3]

        columns = [
            'two_part',
            'Milliseconds',
            'N_E__V',
            'L1_N__V',
            'L2_N__V',
            'L3_N__V',
            'L1_Amp__A',
            'L2_Amp__A',
            'L3_Amp__A',
            'N_Amp__A'
        ]

        values = []
        if monitor_name:
            table = get_monitor_from_tables(monitor_name, event_tables)
            values = [{c: row[c] if c == columns[0] else row[c].tolist() for c in columns} for row in table.where('date == ' + date)]
            if len(values) == 1:
                return ujson.dumps(values[0])

        return '{}'


class DataResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/rms/GREENLN231207/from/2013/08/23/12:00:00/to/2013/08/23/19:15:00/Current_RMS_10_Cycle_Avg_A/VAR_L2_10_Cycle_Max_kVAR
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        from_year = uri_parts[4]
        from_month = uri_parts[5]
        from_day = uri_parts[6]
        from_time = uri_parts[7]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')
        to_year = uri_parts[9]
        to_month = uri_parts[10]
        to_day = uri_parts[11]
        to_time = uri_parts[12]
        to_date_str = to_year + '-' + to_month + '-' + to_day + ' ' + to_time
        to_dt = datetime.datetime.strptime(to_date_str, '%Y-%m-%d %H:%M:%S')

        max_len = len(uri_parts)
        columns = ['date']
        for i in range(13, max_len):
            columns.append(uri_parts[i])

        data = get_data(monitor_name, from_dt, to_dt, columns)
        ret = '{' +\
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"from":"' + from_date_str + '",' + \
            '"to":"' + to_date_str + '",' + \
            '"columns":' + ujson.dumps(columns) + ',' + \
            '"data":' + data + '}'

        return ret


class AnnualHeatMapResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        max_len = len(uri_parts)

        if max_len != 4:
            return ujson.dumps({'error': 'data column not specified'})

        columns = ['date']
        for i in range(3, max_len):
            columns.append(uri_parts[i])

        if len(columns) != 2:
            return ujson.dumps({'error': 'too many columns specified'})


        data = get_data_heat_map(monitor_name, columns)
        ret = '{' + \
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"columns":' + ujson.dumps(columns) + ',' + \
            '"data":' + data + '}'
        return ret


class WaveformResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/waveforms/voltage/ASHTONPK171032/2013/08/10/11:45:00
        #       http://localhost/waveforms/current/ASHTONPK171032/2013/08/10/11:30:00
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        harmonics_type = uri_parts[3]
        from_year = uri_parts[4]
        from_month = uri_parts[5]
        from_day = uri_parts[6]
        from_time = uri_parts[7]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')

        data = get_data_waveform(monitor_name, harmonics_type, from_dt)
        ret = '{' + \
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"from":"' + from_date_str + '",' + \
            '"harmonics_type":"' + harmonics_type + '",' + \
            '"data":' + data + '}'
        return ret


class HarmonicsResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/harmonics/voltage/ASHTONPK171032/2013/08/10/11:45:00
        #       http://localhost/harmonics/current/ASHTONPK171032/2013/08/10/11:30:00
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        harmonics_type = uri_parts[3]
        from_year = uri_parts[4]
        from_month = uri_parts[5]
        from_day = uri_parts[6]
        from_time = uri_parts[7]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')

        show_fundamental = True
        if 'nofundamental' in uri_parts:
            show_fundamental = False

        to_pu = False
        if 'perunit' in uri_parts:
            to_pu = True

        interharmonics = False
        if 'interharmonics' in uri_parts:
            interharmonics = True

        data = get_data_harmonics(monitor_name, harmonics_type, from_dt, show_fundamental, to_pu, interharmonics)
        ret = '{' + \
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"from":"' + from_date_str + '",' + \
            '"harmonics_type":"' + harmonics_type + '",' + \
            '"data":' + data + '}'
        return ret


class HarmonicsTrendsResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/rms/GREENLN231207/from/2013/08/23/12:00:00/to/2013/08/23/19:15:00/Current_RMS_10_Cycle_Avg_A/VAR_L2_10_Cycle_Max_kVAR
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        harmonics_type = uri_parts[3]
        from_year = uri_parts[5]
        from_month = uri_parts[6]
        from_day = uri_parts[7]
        from_time = uri_parts[8]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')
        to_year = uri_parts[10]
        to_month = uri_parts[11]
        to_day = uri_parts[12]
        to_time = uri_parts[13]
        to_date_str = to_year + '-' + to_month + '-' + to_day + ' ' + to_time
        to_dt = datetime.datetime.strptime(to_date_str, '%Y-%m-%d %H:%M:%S')

        show_fundamental = True
        if 'nofundamental' in uri_parts:
            show_fundamental = False

        to_pu = False
        if 'perunit' in uri_parts:
            to_pu = True

        harmonic_numbers = [1, 2, 3, 5, 7, 9, 11, 13, 15, 17]
        data = get_data_harmonic_trends(monitor_name, harmonics_type, harmonic_numbers, from_dt, to_dt, show_fundamental, to_pu)
        ret = '{' +\
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"harmonic_numbers":' + ujson.dumps(harmonic_numbers) + ',' + \
            '"from":"' + from_date_str + '",' + \
            '"to":"' + to_date_str + '",' + \
            '"data":' + data + '}'

        return ret


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
USING_SSL = False
PRECALCULATE_DAILY_RESAMPLING = False
PRECALCULATE_HEATMAP_DATA = False

monitors_list = []
daily_resampled_data = {}
heatmap_precalculated_data = {}
harmonics_tables = {}
C2C_events = {}
# negative_batch_map = {}

if __name__ == '__main__':
    # open database file
    if IN_MEMORY:
        # note that 'driver_core_backing_store=0' disables persisting changes to disk
        h5file = tables.open_file(FILENAME, driver="H5FD_CORE", driver_core_backing_store=0)
    else:
        h5file = tables.open_file(FILENAME)
    monitor_tables = h5file.root

    # find_negative_real_power_measurements()

    if INDIVIDUAL_HARMONICS:
        for f in HARMONICS_FILENAMES:
            h5file = tables.open_file(HARMONICS_FILENAMES[f])
            harmonics_tables[f] = h5file.root

    h5file = tables.open_file(EVENT_FILENAME)
    event_tables = h5file.root

    precalculate_monitors_list()
    precalculate_C2C_events()

    if PRECALCULATE_DAILY_RESAMPLING:
        precalculate_daily_resampling()

    if PRECALCULATE_HEATMAP_DATA:
        precalculate_heat_map_data()

    if USING_SSL:
        sslContext = ssl.DefaultOpenSSLContextFactory(
            '/cert/privkey.pem', 
            '/cert/cacert.pem',
        )

    root = File("web")
    root.putChild('rms', resource.EncodingResourceWrapper(DataResource(), [server.GzipEncoderFactory()]))
    root.putChild('monitors', resource.EncodingResourceWrapper(MonitorsResource(), [server.GzipEncoderFactory()]))
    root.putChild('heatmap', resource.EncodingResourceWrapper(AnnualHeatMapResource(), [server.GzipEncoderFactory()]))
    root.putChild('waveforms', resource.EncodingResourceWrapper(WaveformResource(), [server.GzipEncoderFactory()]))
    root.putChild('harmonics', resource.EncodingResourceWrapper(HarmonicsResource(), [server.GzipEncoderFactory()]))
    root.putChild('harmonicstrends', resource.EncodingResourceWrapper(HarmonicsTrendsResource(), [server.GzipEncoderFactory()]))
    root.putChild('events', resource.EncodingResourceWrapper(EventsResource(), [server.GzipEncoderFactory()]))
    root.putChild('event', resource.EncodingResourceWrapper(EventWaveformResource(), [server.GzipEncoderFactory()]))

    if USING_SSL:
        reactor.listenSSL(443, server.Site(resource.EncodingResourceWrapper(root, [server.GzipEncoderFactory()])), sslContext)
    else:
        reactor.listenTCP(80, server.Site(root))

    reactor.run()
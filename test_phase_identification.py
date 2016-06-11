import numpy as np

def add_angle(a, b):
    total = a + b
    if (total >= 360.0):
        total = total - 360.0
    return total

def sub_angle(a, b):
    total = a - b
    if (total < 0.0):
        total = 360.0 - total
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

def neg_seq_mag_same_mags(a, b, c):
    b_ang_new = add_angle(b[1], 240.0)
    c_ang_new = add_angle(c[1], 120.0)

    re = np.cos(a[1] * np.pi / 180.0) + np.cos(b_ang_new * np.pi / 180.0) + np.cos(c_ang_new * np.pi / 180.0)
    im = np.sin(a[1] * np.pi / 180.0) + np.sin(b_ang_new * np.pi / 180.0) + np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def pos_seq_mag(a, b, c):
    b_ang_new = add_angle(b[1], 120.0)
    c_ang_new = add_angle(c[1], 240.0)

    re = a[0] * np.cos(a[1] * np.pi / 180.0) + b[0] * np.cos(b_ang_new * np.pi / 180.0) + c[0] * np.cos(c_ang_new * np.pi / 180.0)
    im = a[0] * np.sin(a[1] * np.pi / 180.0) + b[0] * np.sin(b_ang_new * np.pi / 180.0) + c[0] * np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def approx_equal(a, b, tol):
    return abs(a - b) < tol

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
        return 0
    if phasor > 210.0 and phasor <= 270.0:
        return 1
    if phasor > 90.0 and phasor <= 150.0:
        return 2
    if phasor > 150.0 and phasor <= 210.0:
        return 0
    if phasor > 30.0 and phasor <= 90.0:
        return 1
    if phasor > 270.0 and phasor <= 330.0:
        return 2

def identify_phase_polarity(phasor):
    if phasor > 330.0 or phasor <= 30.0:
        return 1
    if phasor > 210.0 and phasor <= 270.0:
        return 1
    if phasor > 90.0 and phasor <= 150.0:
        return 1
    if phasor > 150.0 and phasor <= 210.0:
        return -1
    if phasor > 30.0 and phasor <= 90.0:
        return -1
    if phasor > 270.0 and phasor <= 330.0:
        return -1

# def any_negative_phase(a, b, c):
#     # a[1] between 90 and 270
#     if a[1] >= 90.0 and a[1] < 270.0:
#         return True

#     # b[1] between 315 and 135 (wrapped around zero)
#     if b[1] >= 330.0 or b[1] < 150.0:
#         return True

#     # c[1] between 45 and 225
#     if c[1] >= 210.0 or c[1] < 30.0:
#         return True


#     # a[1] between 90 and 270
#     if b[1] >= 90.0 and b[1] < 270.0:
#         return True

#     # b[1] between 315 and 135 (wrapped around zero)
#     if c[1] >= 330.0 or c[1] < 150.0:
#         return True

#     # c[1] between 45 and 225
#     if a[1] >= 210.0 or a[1] < 30.0:
#         return True


#     # a[1] between 90 and 270
#     if c[1] >= 90.0 and c[1] < 270.0:
#         return True

#     # b[1] between 315 and 135 (wrapped around zero)
#     if a[1] >= 330.0 or a[1] < 150.0:
#         return True

#     # c[1] between 45 and 225
#     if b[1] >= 210.0 or b[1] < 30.0:
#         return True

#     return False

def any_negative_phase(a, b, c):
    # a[1] between 90 and 270
    if a[1] >= 90.0 and a[1] < 270.0:
        return True

    # b[1] between 330 and 150 (wrapped around zero)
    if b[1] >= 330.0 or b[1] < 150.0:
        return True

    # c[1] between 30 and 210
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


# List of test phasors (which could represent voltage or current) with manually calculated results.
# 'pf' is a shortcut for rotating all phasors by a given amount.
# It should be noted that a real PQ monitor may make calculated power factor available, which could be used to help detect polarity errors.
tests = [
    # test power factor limits
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 1.00, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': True},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.867, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': True},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.85, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': False},

    # test low magnitude
    {'phasors': [(0.01, 0.0), (0.01, 240.0), (0.01, 120.0)], 'pf': 1.0, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': True},
    {'phasors': [(0.01, 0.0), (0.01, 240.0), (0.01, 120.0)], 'pf': 0.867, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': True},
    {'phasors': [(0.01, 0.0), (0.01, 240.0), (0.01, 120.0)], 'pf': 0.85, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': False},

    # test slight variation on all parameters
    {'phasors': [(0.9, 25.0), (0.8, 236.0), (0.7, 124.0)], 'pf': 1.0, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': True},

    # test slight variation on all parameters, with different power factor for phase C
    # (it's not required to deal with different power factors (leading or lagging) on each phases: historical data at secondary substations shows they are well-correlated over time)
    {'phasors': [(0.9, 25.0), (0.8, 236.0), (0.7, 104.0)], 'pf': 1.0, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': False},

    # test all phases wrong polarity
    {'phasors': [(1.0, 180.0), (1.0, 60.0), (1.0, 300.0)], 'pf': 1.0, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (-1, -1, -1), 'can_be_corrected': True},
    {'phasors': [(1.0, 180.0), (1.0, 60.0), (1.0, 300.0)], 'pf': 0.87, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (-1, -1, -1), 'can_be_corrected': True},

    # test two phases wrong polarity
    {'phasors': [(1.0, 0.0), (1.0, 60.0), (1.0, 300.0)], 'pf': 1.0, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, -1, -1), 'can_be_corrected': True},

    # test one phase wrong polarity
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 300.0)], 'pf': 1.0, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, -1), 'can_be_corrected': True},

    # test wrong sequence
    {'phasors': [(1.0, 0.0), (1.0, 120.0), (1.0, 240.0)], 'pf': 1.0, 'correct_phase_order': (0, 2, 1), 'correct_polarity': (1, 1, 1), 'can_be_corrected': True},

    # test wrong sequence and polarity
    {'phasors': [(1.0, 240.0), (1.0, 0.0), (1.0, 120.0)], 'pf': 1.0, 'correct_phase_order': (1, 0, 2), 'correct_polarity': (1, 1, 1), 'can_be_corrected': True},
]

phase_orders = [(0,1,2), (0,2,1), (1,0,2), (1,2,0), (2,0,1), (2,1,0)]
polarities = [(1,1,1), (-1,1,1), (1,-1,1), (1,1,-1), (-1,-1,1), (-1,1,-1), (1,-1,-1), (-1,-1,-1)]

for i, test in enumerate(tests):
    # print 'test', str(i) +':'

    pf_angle = np.degrees(np.arccos(test['pf']))
    # print pf_angle

    a = (test['phasors'][0][0], add_angle(test['phasors'][0][1], pf_angle))
    b = (test['phasors'][1][0], add_angle(test['phasors'][1][1], pf_angle))
    c = (test['phasors'][2][0], add_angle(test['phasors'][2][1], pf_angle))

    # print neg_seq_mag(a, b, c) > 0.5, any_incorrect_phase(a, b, c)
    if (neg_seq_mag(a, b, c)) > 0.5 or any_incorrect_phase(a, b, c):
        phase_A, offset = find_phase_A_index_and_offset([a[1], b[1], c[1]])
        # print 'phase_A, offset:', phase_A, offset

        test['phase_order'] = (identify_phase(sub_angle(a[1], offset)), identify_phase(sub_angle(b[1], offset)), identify_phase(sub_angle(c[1], offset)))
        test['polarity'] = (identify_phase_polarity(sub_angle(a[1], offset)), identify_phase_polarity(sub_angle(b[1], offset)), identify_phase_polarity(sub_angle(c[1], offset)))
    else:
        test['phase_order'] = (0, 1, 2)
        test['polarity'] = (1, 1, 1)

    # print 'phase_order       ', test['phase_order']
    # print 'polarity          ', test['polarity']
    # print 'phasors           ', a, b, c
    # print 'pos seq           ', '{:.2f}'.format(pos_seq_mag(a, b, c))
    # print 'neg seq           ', '{:.2f}'.format(neg_seq_mag(a, b, c))
    # print 'neg seq (same mag)', '{:.2f}'.format(neg_seq_mag_same_mags(a, b, c))
    # # print 'pf                ', '{:.2f}'.format(np.cos(a[1])), '{:.2f}'.format(np.cos(b[1])), '{:.2f}'.format(np.cos(c[1]))
    # print ''

    # print '  phase order', test['phase_order']
    # print '  polarity   ', test['polarity']

    if test['phase_order'] == test['correct_phase_order'] and test['polarity'] == test['correct_polarity']:
        if test['can_be_corrected'] == True:
            test['passed'] = 1
            # print '  passed'
        else:
            test['passed'] = 0
            # print '  failed'
    else:
        if test['can_be_corrected'] == False:
            # print '  passed'
            test['passed'] = 1
        else:
            test['passed'] = 0
            # print '  failed'

print sum([t['passed'] for t in tests]), 'passed out of', len(tests)
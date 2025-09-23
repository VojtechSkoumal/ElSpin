OPERATING_SETTINGS = {
    '0':10,  # (step pulse, usec)
    '1':25,  # (step idle delay, msec)
    '2':0,  # (step port invert mask:00000000)
    '3':7,  # dir port invert mask (7 = 0b111, all inverted)
    '4':0,  # (step enable invert, bool)
    '5':0,  # (limit pins invert, bool)
    '6':0,  # (probe pin invert, bool)
    
    '10':19,  # status report mask (status, position, hard limits)
    '11':0.010,  # (junction deviation, mm)
    '12':0.002,  # (arc tolerance, mm)
    '13':0,  # (report inches, bool)

    '20':0,  # Soft limits enabled
    '21':1,  # Hard limits enabled
    '22':1,  # Homing cycle enabled
    '23':7,  # Homing dir invert mask (7 = 0b111, all inverted)
    '24':50,  # Homing feed rate
    '25':200,  # Homing seek rate
    '26':250,  # (homing debounce, msec)
    '27':5,  # Homing pull-off (in mm)

    # For pumps (X and Y axes), we set steps per mm such that 1 mm/min = 1 ml/h
    # The actual volume pumped is then V = Distance / 60 
    # syringe_conts = 8 mm/ml
    # ((N*microsteps)/pitch)*syringe_const/mins_in_h
    '100':427,  # X axis (pump 1) - ((200×32)/2)*8/60 = 426.6667
    '101':427,  # Y axis (pump 2) - ((200×32)/2)*8/60 = 426.6667
    # Z axis is not used for pumps, so we set it to a standard value
    '102':200,  # Z axis steps/mm; (200×8)/8 = 200; (N*microsteps)/pitch

    '110':2000,  # (x max rate, mm/min)
    '111':2000,  # (y max rate, mm/min)
    '112':2000,  # (z max rate, mm/min)
    
    '120':10,  # (x accel, mm/sec^2)
    '121':10,  # (y accel, mm/sec^2)
    '122':100,  # (z accel, mm/sec^2)

    '130':135,  # (x max travel, mm)
    '131':135,  # (y max travel, mm)
    '132':200,  # (z max travel, mm)
}

# Operating settings are used for homing as well. Switching settings after homing leads to issues (X and Y axis linked).
HOMING_SETTINGS = {
    '0':10,  # (step pulse, usec)
    '1':25,  # (step idle delay, msec)
    '2':0,  # (step port invert mask:00000000)
    '3':7,  # dir port invert mask (7 = 0b111, all inverted)
    '4':0,  # (step enable invert, bool)
    '5':0,  # (limit pins invert, bool)
    '6':0,  # (probe pin invert, bool)
    
    '10':19,  # status report mask (status, position, hard limits)
    '11':0.010,  # (junction deviation, mm)
    '12':0.002,  # (arc tolerance, mm)
    '13':0,  # (report inches, bool)

    '20':0,  # Soft limits enabled
    '21':1,  # Hard limits enabled
    '22':1,  # Homing cycle enabled
    '23':7,  # Homing dir invert mask (7 = 0b111, all inverted)
    '24':50,  # Homing feed rate
    '25':200,  # Homing seek rate
    '26':250,  # (homing debounce, msec)
    '27':3,  # Homing pull-off (in mm)

    '100':3200,  # X axis steps/mm; (200×32)/2 = 3200; (N*microsteps)/pitch
    '101':3200,  # Y axis steps/mm; (200×32)/2 = 3200; (N*microsteps)/pitch
    '102':200,  # Z axis steps/mm; (200×8)/8 = 200; (N*microsteps)/pitch

    '110':200,  # (x max rate, mm/min)
    '111':200,  # (y max rate, mm/min)
    '112':2000,  # (z max rate, mm/min)
    
    '120':10,  # (x accel, mm/sec^2)
    '121':10,  # (y accel, mm/sec^2)
    '122':100,  # (z accel, mm/sec^2)

    '130':200,  # (x max travel, mm)
    '131':200,  # (y max travel, mm)
    '132':200,  # (z max travel, mm)
}

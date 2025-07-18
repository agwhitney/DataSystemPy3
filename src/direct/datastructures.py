"""
py2 h5classes.py
"""


from tables import IsDescription, UInt8Col, UInt16Col, Float64Col, StringCol


class AMRSample(IsDescription):
    Counts		  = UInt16Col(8)     # Unsigned short integer         
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte      
    SytemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)     # Signed 64-bit integer


class ACTSample(IsDescription):
    Counts		  = UInt16Col(4)     # Unsigned short integer        
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte      
    SytemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)    # Signed 64-bit integer


class SNDSample(IsDescription):
    Counts	      = UInt16Col(16)    # Unsigned short integer      
    Packagenumber = UInt16Col(1)
    Id            = UInt8Col(1)      # unsigned byte        
    SytemStatus   = UInt8Col(1)      # unsigned byte
    NewSequence   = UInt8Col(1)      # unsigned byte
    MotorPosition = UInt16Col(1)     # Unsigned short integer
    Timestamp     = Float64Col(1)    # Signed 64-bit integer


class ThermistorSample(IsDescription):
    Packagenumber = UInt16Col(1)
    Voltages      = Float64Col(40)     # Unsigned short integer
    Timestamp     = Float64Col(1)      # Signed 64-bit integer


class IMUSample(IsDescription):
    Packagenumber = UInt16Col(1)
    EulerAngles   = Float64Col(3)    
    Position      = Float64Col(3) 
    GPSTime       = Float64Col(1)
    Timestamp     = Float64Col(1)    


class Information(IsDescription):
    General       = StringCol(8192)
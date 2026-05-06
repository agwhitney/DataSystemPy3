import pandas as pd

from processL0b.reader import Reader
from processL0b.utils import find_closest_index, save_cal_file, load_cal_file


# Motor values determined by eye. Nadir from LN2 minimum, Zenith = Nadir + 8000
LN2_TEMP = 77
CALTAR_THERMISTORS = [9, 10, 11, 12, 13, 14, 15, 16]
MOTOR_ZENITH = [11500, 12000]
MOTOR_NADIR = [3500, 4000]




def get_calibration_values(ln2_filename: str) -> pd.DataFrame:
    reader = Reader(ln2_filename)

    # Get rows at nadir for each revolution
    nadir_per_revolution = reader.radiometer.data[
        (reader.radiometer.data['MotorPosition'] > MOTOR_NADIR[0])
        &
        (reader.radiometer.data['MotorPosition'] < MOTOR_NADIR[1])
    ].groupby('Revolution').mean()

    # Same at zenith
    zenith_per_revolution = reader.radiometer.data[
        (reader.radiometer.data['MotorPosition'] > MOTOR_ZENITH[0])
        &
        (reader.radiometer.data['MotorPosition'] < MOTOR_ZENITH[1])
    ].groupby('Revolution').mean()

    # Get temperature at zenith (i.e., of the calibration target)
    i = []
    for timestamp in zenith_per_revolution['Timestamp']:
        i.append( find_closest_index(reader.thermistors.data['Timestamp'], timestamp) )
    mean_caltemp = reader.thermistors.data.iloc[i][CALTAR_THERMISTORS].mean(axis=1).reset_index(drop=True)
    zenith_per_revolution['Temperature'] = mean_caltemp

    # For each channel, gain and offset are determined
    labels = [ch.label for ch in reader.radiometer.channels]
    df = pd.DataFrame({
        'ZenithCounts': zenith_per_revolution[labels].mean(),
        'NadirCounts': nadir_per_revolution[labels].mean(),
    })
    df['Gain'] = (df['ZenithCounts'] - df['NadirCounts']) / (zenith_per_revolution['Temperature'].mean() - LN2_TEMP)
    df['Offset'] = df['ZenithCounts'] - df['Gain'] * zenith_per_revolution['Temperature'].mean()
    df.index.name = 'Channel'
    return df


def apply_calibration_values(calibration: pd.DataFrame, l0b_filename: str) -> pd.DataFrame:
    reader = Reader(l0b_filename)
    brightness_temps = reader.radiometer.data
    for channel in reader.radiometer.channels:
        brightness_temps[channel.label] = (brightness_temps[channel.label] - calibration.loc[channel.label, 'Offset']) / calibration.loc[channel.label, 'Gain']
    
    return brightness_temps


if __name__ == '__main__':
    df = load_cal_file("calfile.csv")

    bf = apply_calibration_values(df, "C:\\Users\\agwhi\\Desktop\\cristal\\data413\\l0b\\26_04_13__13_29_44__cristalANT.h5")
    print(bf.head())
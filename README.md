# sma_logger

#   H5LoggSolar.py
#
#   Connects to SMA inverter by modbus and collect data.
#   All data is sent to global MQTT in Kjula DC as JSON.
#
#   Due to some issues with the current firmware(?) it's not possibl to get the daily yield.
#   A workaround is implemented for this: We save the current total yield at midnight
#   and calculates the daily value as the difference from current total yield.

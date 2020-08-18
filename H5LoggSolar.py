#!/usr/bin/env python
#
#   H5LoggSolar.py
#
#   Connects to SMA inverter by modbus and collect data.
#   All data is sent to global MQTT in Kjula DC as JSON.
#
#   Due to some issues with the current firmware(?) it's not possibl to get the daily yield.
#   A workaround is implemented for this: We save the current total yield at midnight
#   and calculates the daily value as the difference from current total yield.
#
#   (C) Ronny Karlsson, 2020-08-13
#

# Imports

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import os.path
from datetime import date
from datetime import datetime
import json

# readSMA function, collects data from inverter, format a JSON and sends to MQTT

def readSMA():
   # Serial number (used as device id in Elastic)
    result = client.read_input_registers(address=30057, count=2, unit=3)
    if result:
       decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big)
       serialno = decoder.decode_32bit_uint()

   # Status. 886 = All ok.
    result = client.read_input_registers(address=30213, count=2, unit=3)
    if result:
       decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big)
       status = decoder.decode_32bit_uint()

   # total_kWh
    result = client.read_input_registers(address=30529, count=2, unit=3)
    if result:
       decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big)
       total_kWh = decoder.decode_32bit_uint()

   # current_W
    result = client.read_input_registers(address=30775, count=2, unit=3)
    if result:
       decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big)
       current_W = decoder.decode_32bit_uint()

   # The inverter returns current_W as high-value when no production. We want zero.
    if current_W > 10000:
       current_W = 0

   # It seems not possible to retrieve the daily yield by modbus. Let's do a workaround for the time beeing...
    today_kWh = dailyYield(total_kWh)

   # Send all data to MQTT
    sendMQTT(serialno, status, current_W, today_kWh, total_kWh)

# dailyYield function. At midnight - or in fact at first run of the day - we are saving the current total to file.
#                      This is then used during the day to calculate the current daily production.

def dailyYield(total_kwh):
    today = date.today()
    currentDateFile = "DailySunInit_" + today.strftime("%Y%m%d")
    if os.path.isfile(currentDateFile):
       pass
    else:
       f = open(currentDateFile, "w") # For the first run of the day - create file and write current Wh
       txt = str(total_kwh) + "\n"
       f.write(txt)
       f.close()

    f = open(currentDateFile, "r")
    dayInit = f.readline()
    y = total_kwh - int(dayInit)
    return y

# sendMQTT function. Put data in a JSON and publish to MQTT

def sendMQTT(serialno, status, current_W, today_kWh, total_kWh):

    # Construct JSON for Global logg
    data = {}
    data['msg_timestamp'] = str(datetime.now())
    data['solarlogg'] = []
    data['solarlogg'].append({
         'source': serialno,
         'status': status,
         'current_W': current_W,
         'today_kWh': today_kWh,
         'total_kWh': total_kWh
          })

    # Set up MQTT parameters
    broker_address="xxxxx.se"
    auth = {'username':"xxxxx", 'password':"xxxxx"}
    current_site = "heron5"
    solar_update_topic = "logger/solar/" + current_site

    try:
        publish.single(solar_update_topic, payload=json.dumps(data), hostname=broker_address, auth=auth, port=1883)
    except Exception as e:
        print e


if __name__ == "__main__":
    client = ModbusClient('192.168.1.131', port=502)
    client.connect()
    readSMA()
    client.close()
#!/usr/bin/env python3
# By: SA2KNG
# Tested on hamlib-4.5 and ic-910h

import argparse
import json
import requests
import socket
from time import sleep

# Perhaps in the future use https://db.satnogs.org/api/transmitters/?format=json
# Sat list: name, dn_lo, dn_hi, up_lo, up_hi
satellites = [
    ['AO-7', 145925000, 145975000, 4320125000, 432175000],  # 7530 Oscar 7
    ['AO-27', 436798000, 436798000, 145850000, 145850000],  # 22825 EYESAT-1
    ['AO-73', 145950000, 145970000, 435130000, 435150000],  # 39444 FUNCUBE-1
    ['AO-91', 145960000, 145960000, 435250000, 435250000],  # 43017 FOX-1B
    ['AO-92', 145880000, 145880000, 435350000, 435350000],  # 43137 FOX-1D
    ['AO-109', 435760000, 435790000, 145860000, 145890000],  # 47311 FOX-1E
    ['ARISS', 437800000, 437800000, 145990000, 145990000],  # 25544 ISS
    ['CAS-3H', 437200000, 437200000, 144350000, 144350000],  # 40908 Lilacsat-2
    ['CAS-4A', 145860000, 145880000, 435210000, 435230000],  # 42761 ZHUHAI-1 OVS-1A
    ['CAS-4B', 145915000, 145935000, 435270000, 435290000],  # 42759 ZHUHAI-1 OVS-1B
    ['FO-118', 435525000, 435555000, 145805000, 145835000],  # 54684 CAS-5A
    ['EO-88', 145960000, 145990000, 435015000, 435045000],  # 42017 Nayif-1
    ['FO-29', 435800000, 435900000, 145900000, 146000000],  # 24278 JAS-2
    ['FO-99', 435880000, 435910000, 145900000, 145930000],  # 43937 NEXUS
    ['HO-113', 435165000, 435195000, 145855000, 145885000],  # 50466 XW-3/CAS-9
    ['IO-86', 435880000, 435880000, 145880000, 145880000],  # 40931 LAPAN-A2
    ['IO-117', 435310000, 435310000, 435310000, 435310000],  # 53106 GreenCube
    ['JO-97', 145855000, 145875000, 435100000, 435120000],  # 43803 JY1Sat
    ['PO-101', 145900000, 145900000, 437500000, 437500000],  # 43678 Diwata-2
    # ['QO-100'],
    ['RS-44', 435610000, 435670000, 145935000, 145995000],  # 44909 Dosaaf-85
    ['SO-50', 436795000, 436795000, 145850000, 145850000],  # 27607 Saudisat-1C
    ['TO-108', 145915000, 145935000, 435270000, 435290000],  # 44881 CAS-6
    ['UVSQ', 437020000, 437020000, 145905000, 145905000],  # 47438 Latmos-1
    ['XW-2A', 145665000, 145685000, 435030000, 435050000],  # 40903 CAS-3A
    ['XW-2B', 145730000, 145750000, 435090000, 435110000],  # 40911 CAS-3B
    ['XW-2C', 145795000, 145815000, 435150000, 435170000],  # 40906 CAS-3C
    ['XW-2D', 145860000, 145880000, 435210000, 435230000],  # 40907 CAS-3D
    ['XW-2E', 145915000, 145935000, 435518000, 435538000],  # 40909 CAS-3E
    ['XW-2F', 145980000, 146000000, 435330000, 435350000],  # 40910 CAS-3F
]
tolerance = 0.000035  # doppler tolerance for LEO


def main():
    parser = argparse.ArgumentParser(description='Send rig data to CloudLog')
    parser.add_argument('-a', '--apikey', default='', type=str, help='API Key', required=True)
    parser.add_argument('-u', '--apiurl', default='http://localhost:9005/api/radio', type=str, help='API URL')
    parser.add_argument('-n', '--name', default='Radio', type=str, help='Radio name')
    parser.add_argument('-r', '--righost', default='localhost', type=str, help='rigctld host')
    parser.add_argument('-p', '--rigport', default=4532, type=int, help='rigctl port')
    parser.add_argument('-v', '--verbosity', action='count', default=0, help='Increase verbosity')
    args = parser.parse_args()

    rig = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rig.connect((args.righost, args.rigport))
    rig.settimeout(2.0)

    s = requests.Session()
    while True:
        try:
            vfoa = int(hamlib_query(rig, 'f')[0])
            modea = hamlib_query(rig, 'm')[0]
            vfob = int(hamlib_query(rig, 'i')[0])
            modeb = hamlib_query(rig, 'x')[0]
            split = hamlib_query(rig, 's')  # Detect radio mode and adjust API accordingly
            api = {'key': args.apikey, 'radio': args.name, 'frequency': vfob, 'mode': modeb,
                   'frequency_rx': vfoa, 'mode_rx': modea, 'prop_mode': 'SAT', 'sat_name': find_sat(vfob, vfoa)}
            try:
                s.post(args.apiurl, data=json.dumps(api))
            except socket.error as e:
                print(f'Connection Failed due to socket - {e}')
            print(f'Sat: {api["sat_name"]}, Dn: {vfoa} {modea} Up: {vfob} {modeb}, split: {split}')
            sleep(2)
        except KeyboardInterrupt or requests.exceptions.ConnectionError:
            break
    rig.close()
    print('Exiting')


def find_sat(uplink, downlink):
    for i in satellites:
        if len(i) != 5:
            continue
        if i[3] * (1 - tolerance) < uplink < i[4] * (1 + tolerance) and \
           i[1] * (1 - tolerance) < downlink < i[2] * (1 + tolerance):
            return i[0]
    return ''


def hamlib_query(r, cmd):
    r.sendall(bytes(f'+{cmd}\n', encoding='ascii'))
    try:
        data = r.recv(1024).splitlines()
    except TimeoutError:
        return None
    if len(data) < 2:
        print(f'bad response: {data}')
        return None
    if data[-1] != b'RPRT 0':
        print(f'bad report: {data[-1]}')
        return None
    return [d.decode().split(':')[1].strip() for d in data[1:-1]]


if __name__ == '__main__':
    main()

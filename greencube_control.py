#!/usr/bin/env python3
import argparse
import maidenhead
from skyfield.api import load, wgs84
import socket
from time import sleep


def main():
    parser = argparse.ArgumentParser(description='Control radio doppler for greencube')
    parser.add_argument('-l', '--locator', required=True, help='Your maidenhead locator')
    parser.add_argument('-e', '--elevation', default=0, type=int, help="Your elevation")
    parser.add_argument('-f', '--freq', default=435310000, type=int, help='Frequency to track')
    parser.add_argument('-t', '--tunestep', default=50, type=int, help='TX tuning step')
    parser.add_argument('-n', '--norad', default=53106, type=int, help='NORAD ID to track')
    parser.add_argument('-r', '--righost', default='localhost', type=str, help='rigctld host')
    parser.add_argument('-p', '--rigport', default=4532, type=int, help='rigctl port')
    parser.add_argument('-v', '--verbosity', action='count', default=0, help='Increase verbosity')
    args = parser.parse_args()

    lat, lon = maidenhead.to_location(args.locator, center=True)
    qth = wgs84.latlon(lat, lon, args.elevation)
    print(f'Locator {args.locator}, Lat {lat}, Lon {lon}')

    satellite = from_nasabare(args.norad)
    if not satellite or abs(load.timescale().now() - satellite.epoch) > 14:
        satellite = from_nasabare(args.norad, True)

    print(f'Sat: {satellite}')
    print(f'Base frequency {args.freq/1000000:.03f} MHz')

    rig = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rig.connect((args.righost, args.rigport))
    rig.settimeout(2.0)
    for q in ['S 1 VFOB', 'M USB 2300', 'X USB 2300']:  # Initialize radio
        rig_query(rig, q)

    rx_old = tuning = up_old = 0
    while True:
        try:
            pos = (satellite - qth).at(load.timescale().now())
            _, _, _, _, _, range_rate = pos.frame_latlon_and_rates(qth)
            doppler = int(range_rate.km_per_s / 299792 * args.freq)
            if rig_query(rig, 't') != '0':
                continue
            rx = int(rig_query(rig, 'f'))
            if rx_old > 0:
                tuning += rx - rx_old
            uplink = args.freq + doppler + tuning
            downlink = args.freq - doppler + tuning
            rx_old = downlink
            print(f'speed {range_rate.km_per_s:.02f} km/s, doppler {doppler:.0f}, '
                  f'uplink {uplink:.0f}, downlink {downlink:.0f}, tuning {tuning}')
            rig_query(rig, f'F {downlink}')
            if abs(uplink - up_old) > args.tunestep:
                # print('set uplink')
                rig_query(rig, f'I {uplink}')
                up_old = uplink
            sleep(1)
        except KeyboardInterrupt:
            break
    rig_query(rig, 'S 0 VFOA')  # Disable split mode
    rig.close()
    print('Exiting')


def from_nasabare(norad, reload=False):
    nasabare = 'https://www.amsat.org/tle/current/nasabare.txt'
    satellites = load.tle_file(nasabare, filename='nasabare.txt', reload=reload)
    by_number = {sat.model.satnum: sat for sat in satellites}
    try:
        return by_number[norad]  # If ID is missing throws KeyError
    except KeyError:
        return None


def rig_query(rig, cmd):
    rig.sendall(bytes(f'+{cmd}\n', encoding='ascii'))
    try:
        data = rig.recv(1024).splitlines()
    except TimeoutError:
        return None
    if len(data) < 2:
        print('bad response')
        return None
    if data[-1] != b'RPRT 0':
        print('bad report')
        return None
    return data[-2].decode().split(':')[1].strip()


if __name__ == '__main__':
    main()

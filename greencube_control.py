#!/usr/bin/env python3
import argparse
import maidenhead
from skyfield.api import load, wgs84
import socket
from time import sleep


def main():
    parser = argparse.ArgumentParser(description='Control radio doppler for greencube')
    parser.add_argument('-l', '--locator', required=True, help='Your maidenhead locator')
    parser.add_argument('-e', '--elevation', default=0, type=int, help='Your elevation')
    parser.add_argument('-z', '--horizon', default=0, type=float, help='Above this horizon to track rotator')
    parser.add_argument('-f', '--freq', default=435310000, type=int, help='Frequency to track')
    parser.add_argument('-t', '--tunestep', default=50, type=int, help='TX tuning step')
    parser.add_argument('-d', '--disable_tune', action='store_true', help='Disable VFO tuning on radio')
    parser.add_argument('-n', '--norad', default=53106, type=int, help='NORAD ID to track')
    parser.add_argument('-r', '--righost', default='localhost', type=str, help='rigctld host')
    parser.add_argument('-p', '--rigport', default=4532, type=int, help='rigctl port')
    parser.add_argument('-R', '--rothost', default='', type=str, help='rotctld host')
    parser.add_argument('-P', '--rotport', default=4533, type=int, help='rotctl port')
    parser.add_argument('-T', '--threshold', default=5, type=int, help='rotctl move threshold')
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
        hamlib_query(rig, q)

    rot = None
    if len(args.rothost) > 0:
        rot = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rot.connect((args.rothost, args.rotport))
        rot.settimeout(2.0)

    rx_old = tuning = up_old = alt_old = az_old = 0
    while True:
        try:
            pos = (satellite - qth).at(load.timescale().now())
            _, _, _, _, _, range_rate = pos.frame_latlon_and_rates(qth)
            alt, az, _ = pos.altaz()
            doppler = int(range_rate.km_per_s / 299792 * args.freq)
            if alt.degrees < args.horizon:
                t, events = satellite.find_events(qth, load.timescale().now(), load.timescale().now() + 1/6,
                                                  altitude_degrees=args.horizon)
                alt, az, _ = (satellite - qth).at(t[0]).altaz()
            if hamlib_query(rig, 't') != '0':
                continue
            if not args.disable_tune:
                rx = int(hamlib_query(rig, 'f'))
                if rx_old > 0:
                    tuning += rx - rx_old
            uplink = args.freq + doppler + tuning
            downlink = args.freq - doppler + tuning
            rx_old = downlink
            print(f'speed {range_rate.km_per_s:.02f} km/s, doppler {doppler:.0f}, '
                  f'alt {alt.degrees:.01f}, az {az.degrees:.01f}, '
                  f'uplink {uplink:.0f}, downlink {downlink:.0f}, tuning {tuning}')
            hamlib_query(rig, f'F {downlink}')
            if abs(uplink - up_old) > args.tunestep:
                # print('set uplink')
                hamlib_query(rig, f'I {uplink}')
                up_old = uplink
            if abs(az.degrees - az_old) > args.threshold or abs(alt.degrees - alt_old) > args.threshold:
                if rot:
                    hamlib_query(rot, f'P {az.degrees:.02f} {alt.degrees:.02f}')
                else:
                    print(f'P {az.degrees:.02f} {alt.degrees:.02f}')
                az_old = az.degrees
                alt_old = alt.degrees
            sleep(1)
        except KeyboardInterrupt:
            break
    hamlib_query(rig, 'S 0 VFOA')  # Disable split mode
    rig.close()
    if rot:
        rot.close()
    print('Exiting')


def from_nasabare(norad, reload=False):
    nasabare = 'https://www.amsat.org/tle/current/nasabare.txt'
    satellites = load.tle_file(nasabare, filename='nasabare.txt', reload=reload)
    by_number = {sat.model.satnum: sat for sat in satellites}
    try:
        return by_number[norad]  # If ID is missing throws KeyError
    except KeyError:
        return None


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
    return data[-2].decode().split(':')[1].strip()


if __name__ == '__main__':
    main()

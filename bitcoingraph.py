# Copyright (c) 2022-2023, J-Michael Roberts, Corvus Forensics
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Adapted from Kevin Perlow's code at
# https://github.com/kevinperlow/SANS-DFIR-2017/blob/master/bitcoinmapping.py
# and updated to function with different API.

# This code requires an API key from blockchair.com.
# You can get one for cheap at:
# https://blockchair.com/api/plans
# and then add it to the apikeyval variable below.

import json
import requests
import argparse
import sys
import re
from datetime import datetime

def writesource(hashvar, jsondata, type):
    # function to save downloaded source data to local files
    if type == 'a':
        folder = 'data/address/'
    elif type == 't':
        folder = 'data/transaction/'
    else:
        sys.exit('Weird. This code failed to define the data type to save.')

    with open(folder+hashvar+'.json', 'w+') as f:
        f.write(json.dumps(jsondata))
    f.close()
    return

def localjson(type, hash):
    # read local data type address or transaction
    try:
        with open('data/'+type+'/'+hash+'.json', 'r') as locjson:
            jsondata = json.load(locjson)
    except FileNotFoundError:
        return False
    if type == 'address':
        return jsondata
    elif type == 'transaction':
        return jsondata['data'][hash]
    else:
        return False

def netjson(type, hash, apikey):
    # pull json data from the internet
    apikeyval = '?key=' + apikey
    if type == 'address':
        adendpoint = 'https://api.blockchair.com/bitcoin/dashboards/address/'
        reqbase = adendpoint + hash
        reqjson = (requests.get(reqbase+apikeyval)).json()
        if reqjson['context']['code'] == 432:
            sys.exit(reqjson['context']['error'])
        writesource(hash, reqjson, 'a')
        addrdict = reqjson['data'][hash]
        return addrdict
    elif type == 'transaction':
        txendpoint = 'https://api.blockchair.com/bitcoin/dashboards/transaction/'
        txhash = hash
        txreqbase = txendpoint + txhash
        txreqjson = (requests.get(txreqbase+apikeyval)).json()
        if txreqjson['context']['code'] == 432:
            sys.exit(txreqjson['context']['error'])
        writesource(txhash, txreqjson, 't')
        txdict = txreqjson['data'][txhash]
        return txdict

def graphaddress(seedaddress, apikey, timefield, valopts, netstate):
    z = 0
    i = 0
    # fetch address info
    if netstate < 2:
        # attempt to read from files first
        reqjson = localjson('address', seedaddress)
        if reqjson:
            addrdict = reqjson['data'][seedaddress]
        elif reqjson == False and netstate > 0:
            addrdict = netjson('address', seedaddress, apikey)
        else:
            if args.warn:
                print('Warning: Local data for address ' + seedaddress + ' unavailable.')
            else:
                sys.exit('Local data for address ' + seedaddress + ' unavailable. Exiting')
    else:
        addrdict = netjson('address', seedaddress, apikey)

    if addrdict['address']['transaction_count'] == 0:
        print('Address', seedaddress, 'has no transactions.')
        return

    graphvizlines = []
    addresslist = []
    usedaddresslist = []

    addresslist.append(seedaddress)
    usedaddresslist.append(seedaddress)

    while i < 6:
        if z == 1:
            if netstate < 2:
                # attempt to read from files first
                reqjson = localjson('address', addresslist[i])
                if reqjson:
                    addrdict = reqjson['data'][addresslist[i]]
                elif reqjson == False and netstate > 0:
                    addrdict = netjson('address', addresslist[i], apikey)
                else:
                    if args.warn:
                        print('Warning: Local data for address ' + seedaddress + ' unavailable.')
                    else:
                        sys.exit('Local data for address ' + seedaddress + ' unavailable. Exiting')
            else:
                addrdict = netjson('address', addresslist[i], apikey)

            print('Address: ' + addresslist[i])
        else:
            print('Address: ' + seedaddress)

        for transaction in addrdict['transactions']:
            payerlist = []
            recipientlist = []

            # fetch the transaction info
            print('Transaction: ' + transaction)
            if netstate < 2:
                # attempt to read from files first
                txdict = localjson('transaction', transaction)
                if txdict == False and netstate > 0:
                    txdict = netjson('transaction', transaction, apikey)
                elif txdict == False and netstate == 0:
                    if args.warn:
                        print('Warning: Local data for address ' + seedaddress + ' unavailable.')
                    else:
                        sys.exit('Local data for address ' + seedaddress + ' unavailable. Exiting')
            else:
                txdict = netjson('transaction', transaction, apikey)

            for item in txdict['inputs']:
                payerlist.append(item['recipient'])
                if item['recipient'] not in addresslist:
                    addresslist.append(item['recipient'])

            for target in txdict['outputs']:
                if 'btc' in valopts:
                    btcval = '\\n' + 'BTC' + str(target['value'] / 10000000) + " / "
                else:
                    btcval = '\\n'
                if 'usd' in valopts:
                    usdval = 'USD' + str(target['value_usd'])
                else:
                    usdval = ''
                valstr = btcval + usdval
                valstr = valstr.rstrip(' / ')

                if timefield == 'full':
                    timevar = target['time'] + valstr
                elif timefield == 'date':
                    timevar = target['date'] + valstr
                else:
                    timevar = valstr.lstrip('\\n')
                recipientlist.append([target['recipient'],timevar])
                if target['recipient'] not in addresslist:
                    addresslist.append(target['recipient'])

            for payer in payerlist:
                for recipient,timestamp in recipientlist:
                    if timevar != '':
                        timestampfmt = ' [label="' + timestamp + '" decorate=false]'
                    else:
                        timestampfmt = ''
                    a = '"' + payer + '"' + " -> " + '"' + recipient + '"' + timestampfmt + ';'
                    if a not in graphvizlines:
                        graphvizlines.append(a)
        i = i + 1
        z = 1

    # generate graphviz dot graph data file
    dotgraph = 'data/' + seedaddress + '.dot'
    with open(dotgraph,'w') as g:
        g.write('digraph {\nrankdir=LR;\n')

        for each in graphvizlines:
        	g.write(str(each) + '\n')

        g.write('}\n')
    g.close()
    return

def graphloop(targetlist):
    # breaking out for future TODO for option to bypass and just re-concatenate
    for seedaddress in targetlist:
        graphaddress(seedaddress, apikey, timefield, valopts, netstate)
    return

def graphconcatenate(targetlist):
    # concatenate all address graphs into a single graph and/or truncate
    if len(targetlist) > 1 or args.truncate:
        alltx = []
        with open('data/'+reporttime+'_graph.dot', 'w') as g:
            g.write('digraph {\n')
            if args.highlight:
                g.write('{\nnode [style=filled]\n')
                for address in targetlist:
                    g.write('"'+address+'" [fillcolor=yellow]\n')
                g.write('}\n')
            g.write('rankdir=LR;\n')
            for address in targetlist:
                try:
                    with open('data/'+address+'.dot', 'r') as h:
                        lines = h.readlines()
                    for line in lines:
                        if args.truncate:
                            # only keep transactions with targetlist
                            txpts = re.findall('[0-9a-zA-Z]+', line)
                            if len(txpts) < 2:
                                continue
                            elif txpts[0] not in targetlist and txpts[1] not in targetlist:
                                continue
                        if ' -> ' in line and line not in alltx:
                            alltx.append(line)
                except:
                    # catching errors that come up when wallets have no transactions
                    pass
            for txline in alltx:
                g.write(txline)
            g.write('}')
    return

def termcolors():
    # define the usual terminal colors
    global trmred
    global trmgrn
    global trmcyn
    global trmyel
    global trmmag
    global trmbmag
    global trmnorm
    global trmclear
    # Set the bits we need for outputting to the terminal - CF standard
    trmred = "\x1B[1m\x1B[31m"  # Bold Red (ANSI) - malware
    trmgrn = "\x1B[0m\x1B[32m"  # Normal Green (ANSI) - clean
    trmcyn = "\x1B[1m\x1B[36m"  # Bold Cyan (ANSI)
    trmyel = "\x1B[0m\x1B[33m"  # Normal Yellow (ANSI) - unknown
    trmmag = "\x1B[35m"  # Magenta (ANSI)
    trmbmag = "\x1B[1m\x1B[35m"  # Bold Magenta (ANSI) - errors
    trmnorm = "\x1B[0m"  # Normal (ANSI) - normal
    trmclear = "\x1b[2K" # Clear line
    return

if __name__ == "__main__":

    arghelpdesc = 'Cryptocurrency Transaction Grapher'
    parser = argparse.ArgumentParser(description=arghelpdesc)
    parser.add_argument('-t', '--time', help='Add full transaction timestamps to each arrow on the graph.', action='store_true')
    parser.add_argument('-d', '--date', help='Add date-only transaction timestamps to each arrow on the graph.', action='store_true')
    parser.add_argument('-btc', '--valuebtc', help='Add transaction value in BTC to each arrow on the graph.', action='store_true')
    parser.add_argument('-usd', '--valueusd', help='Add transaction value in USD to each arrow on the graph.', action='store_true')
    parser.add_argument('-a', '--apikey', help='Blockchair API Key.', nargs=1)
    parser.add_argument('-f', '--file', help='File to read addresses from. One address per line.', nargs=1)
    parser.add_argument('-l', '--local', help='Attempt to find information in local data folders before making API calls.', action='store_true')
    parser.add_argument('-o', '--offline', help='Only work from information saved in local data folders. No API calls will be made.', action='store_true')
    parser.add_argument('-w', '--warn', help='Only warn if missing address and transaction data local folders and proceed anyway.', action='store_true')
    parser.add_argument('--truncate', help='Truncate Graphviz data to only include transactions with the target address(es).', action='store_true')
    parser.add_argument('--highlight', help='Highlight target address(es) on graph.', action='store_true')
    parser.add_argument('address', help='One or more target address(es) to graph.', nargs=argparse.REMAINDER)

    termcolors()

    args = parser.parse_args()

    if args.time and args.date:
        sys.exit(trmred + 'ERROR: Options --time and --date are mutually exclusive.' + trmnorm)
    if args.local and args.offline:
        sys.exit(trmred + 'ERROR: Options --local and --offline are mutually exclusive.' + trmnorm)

    valopts = []
    if args.valuebtc:
        valopts.append('btc')
    if args.valueusd:
        valopts.append('usd')

    reporttime = datetime.now().strftime('%Y%m%d_%H%M%S')

    targetlist=[]

    if args.file:
        try:
            with open(args.file[0]) as asrcfile:
                for line in asrcfile:
                    line = line.strip()
                    if line == '':
                        continue
                    elif re.search('[^0-9a-zA-Z]', line):
                        print(trmyel + 'Skipping possible bad address: ' + line + trmnorm)
                        continue
                    elif len(line) < 27:
                        print(trmyel + 'Skipping possible bad address: ' + line + trmnorm)
                        continue
                    if line not in targetlist:
                        targetlist.append(line)
        except FileNotFoundError:
            sys.exit(trmred + 'Address list file ' + args.file[0] + ' not found.' + trmnorm)

    if args.address:
        for line in args.address:
            line = line.strip()
            if line == '':
                continue
            elif re.search('[^0-9a-zA-Z]', line):
                print(trmyel + 'Skipping possible bad address: ' + line + trmnorm)
                continue
            elif len(line) < 27:
                print(trmyel + 'Skipping possible bad address: ' + line + trmnorm)
                continue
            if line not in targetlist:
                targetlist.append(line)

    if args.time:
        timefield = 'full'
    elif args.date:
        timefield = 'date'
    else:
        timefield = ''

    if args.offline:
        netstate = 0
    elif args.local:
        netstate = 1
    else:
        netstate = 2

    if args.apikey:
        apikey = args.apikey
        # sanity check apikey value?
    else:
        # get API key from file
        try:
            with open('apikey.txt', 'r') as k:
                apikey = k.readline().strip()
            k.close()
        except FileNotFoundError:
            sys.exit(trmyel + 'Create the file apikey.txt and add your API at the top or specify on the command line with the --apikey option.' + trmnorm)

    if len(targetlist) == 0:
        sys.exit('usage: bitcoingraph.py [--help] [--time] [--date] [--apikey] [--file FILE] [--local] [--offline] [--truncate] [--highlight] [address] [address...]')

    graphloop(targetlist)
    graphconcatenate(targetlist)

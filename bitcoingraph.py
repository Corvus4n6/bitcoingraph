# Copyright (c) 2022, J-Michael Roberts, Corvus Forensics
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
    return jsondata

def netjson(type, hash, apikey):
    # pull json data from the internet
    apikeyval = '?key=' + apikey
    if type == 'address':
        adendpoint = 'https://api.blockchair.com/bitcoin/dashboards/address/'
        reqbase = adendpoint + hash
        reqjson = (requests.get(reqbase+apikeyval)).json()
        writesource(hash, reqjson, 'a')
        addrdict = reqjson['data'][hash]
        return addrdict
    elif type == 'transaction':
        txendpoint = 'https://api.blockchair.com/bitcoin/dashboards/transaction/'
        txhash = hash
        txreqbase = txendpoint + txhash
        txreqjson = (requests.get(txreqbase+apikeyval)).json()
        writesource(txhash, txreqjson, 't')
        txdict = txreqjson['data'][txhash]
        return txdict

def graphaddress(seedaddress, apikey, timefield, netstate):
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
            sys.exit('Local data for address ' + seedaddress + ' unavailable.')
    else:
        addrdict = netjson('address', seedaddress, apikey)


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
                    sys.exit('Local data for address ' + addresslist[i] + ' unavailable.')
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
            txdict = netjson('transaction', transaction, apikey)

            for item in txdict['inputs']:
                payerlist.append(item['recipient'])
                if item['recipient'] not in addresslist:
                    addresslist.append(item['recipient'])

            for target in txdict['outputs']:
                if timefield == 'full':
                    timevar = target['time']
                elif timefield == 'date':
                    timevar = target['date']
                else:
                    timevar = ''
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

arghelpdesc = 'Bitcoin Transaction Grapher'
parser = argparse.ArgumentParser(description=arghelpdesc)
parser.add_argument('-t', '--time', help='Add full transaction timestamps to each arrow on the graph.', action='store_true')
parser.add_argument('-d', '--date', help='Add date-only transaction timestamps to each arrow on the graph.', action='store_true')
parser.add_argument('-f', '--file', help='File to read addresses from. One address per line.', nargs=1)
parser.add_argument('-l', '--local', help='Attempt to find information in local data folders before making API calls.', action='store_true')
parser.add_argument('-o', '--offline', help='Only work from information saved in local data folders. No API calls will be made.', action='store_true')
parser.add_argument('--truncate', help='Truncate Graphviz data to only include transactions with the target address(es).', action='store_true')
parser.add_argument('--highlight', help='Highlight target address(es) on graph.', action='store_true')
parser.add_argument('address', help='One or more target address(es) to graph.', nargs=argparse.REMAINDER)

args = parser.parse_args()

if args.time and args.date:
    sys.exit('ERROR: Options --time and --date are mutually exclusive.')
if args.local and args.offline:
    sys.exit('ERROR: Options --local and --local-only are mutually exclusive.')

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
                    print('Skipping possible bad address: ' + line)
                    continue
                elif len(line) < 27:
                    print('Skipping possible bad address: ' + line)
                    continue
                if line not in targetlist:
                    targetlist.append(line)
    except FileNotFoundError:
        sys.exit('Address list file ' + args.file[0] + ' not found.')

if args.address:
    for line in args.address:
        line = line.strip()
        if line == '':
            continue
        elif re.search('[^0-9a-zA-Z]', line):
            print('Skipping possible bad address: ' + line)
            continue
        elif len(line) < 27:
            print('Skipping possible bad address: ' + line)
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

# get API key from file
try:
    with open('apikey.txt', 'r') as k:
        apikey = k.readline().strip()
    k.close()
except FileNotFoundError:
    sys.exit('Create the file apikey.txt and add your API at the top.')

if len(targetlist) == 0:
    sys.exit('usage: bitcoingraph.py [--help] [--time] [--date] [--file FILE] [--local] [--offline] [--truncate] [--highlight] [address] [address...]')

for seedaddress in targetlist:
    graphaddress(seedaddress, apikey, timefield, netstate)

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
        for txline in alltx:
            g.write(txline)
        g.write('}')

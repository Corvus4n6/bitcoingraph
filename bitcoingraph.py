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

z = 0
i = 0

def writesource(hashvar, jsondata, type):
    # function to save downloaded source data to local files
    if type == 'a':
        folder = 'data/address/'
    elif type == 't':
        folder = 'data/transaction/'
    else:
        die('Weird. This code failed to define the data type to save.')

    with open(folder+hashvar+'.json', 'w+') as f:
        f.write(json.dumps(jsondata))
    f.close()
    return

# fetch address info
adendpoint = 'https://api.blockchair.com/bitcoin/dashboards/address/'
seedaddress = input('Enter the seed address: ')
reqbase = adendpoint + seedaddress
apikeyval = '?key=<PUT_YOUR_API_KEY_IN_HERE>'

reqjson = (requests.get(reqbase+apikeyval)).json()
writesource(seedaddress, reqjson, 'a')
addrdict = reqjson['data'][seedaddress]

graphvizlines = []
addresslist = []
usedaddresslist = []

addresslist.append(seedaddress)
usedaddresslist.append(seedaddress)

while i < 6:
    if z == 1:
        reqbase = adendpoint + addresslist[i]
        reqjson = (requests.get(reqbase+apikeyval)).json()
        writesource(seedaddress, reqjson, 'a')
        addrdict = reqjson['data'][addresslist[i]]
        print('Address: ' + addresslist[i])
    else:
        print('Address: ' + seedaddress)

    for transaction in addrdict['transactions']:
        payerlist = []
        recipientlist = []

        # fetch the transaction info
        print('Transaction: ' + transaction)
        txendpoint = 'https://api.blockchair.com/bitcoin/dashboards/transaction/'
        txhash = transaction
        txreqbase = txendpoint + txhash
        txreqjson = (requests.get(txreqbase+apikeyval)).json()
        writesource(txhash, txreqjson, 't')
        txdict = txreqjson['data'][txhash]

        for item in txdict['inputs']:
            payerlist.append(item['recipient'])
            if item['recipient'] not in addresslist:
                addresslist.append(item['recipient'])

        for target in txdict['outputs']:
            recipientlist.append(target['recipient'])
            if target['recipient'] not in addresslist:
                addresslist.append(target['recipient'])

        for payer in payerlist:
            for recipient in recipientlist:
                a = '"' + payer + '"' + " -> " + '"' + recipient + '"' + ";"
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

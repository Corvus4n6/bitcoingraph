# Bitcoingraph

## Description
Simple python code that performs lookups of Bitcoin transactions for a given address and generates Graphviz DOT graph data files to help visualize Bitcoin transactions for humans. It was adapted from Kevin Perlow's code released at the 2017 SANS DFIR summit and available at [https://github.com/kevinperlow/SANS-DFIR-2017](https://github.com/kevinperlow/SANS-DFIR-2017)

This code makes requests to the Blockchair API, which requires a key for access. You can get a key for cheap at [https://blockchair.com/api/](https://blockchair.com/api/)

## Example Graph
The example graph below is a truncated graph showing all Bitcoin addresses that made transactions with address 3L2Uyh1eHpfPyPayqrh5WjfnTzWiG4xPLu. The full graph generated by the code for this address is significantly larger.

![Example graph](example.png)

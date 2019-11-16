# network-protocols
Implementation of Go-Back-N, Selective repeat protocols

## Requirement:

You need python 2.7 version to run this code. To download python 2.7, please refer 

https://www.python.org/downloads/release/python-2712/

## Execution :

### Go-Back-N :
To start the Receiver, please run the following command 

```
python Go-Back-N/receiver.py <port no.>
```

To start the sender, please run the following commands

```
python Go-Back-N/sender.py Go-Back-N/inputfile <port no.> <no. of pkts>
```

### Selective Repeat

```
python Selective\ Repeat/receiver.py <port no.>
```

To start the sender, please run the following commands

```
python Selective\ Repeat/sender.py Selective\ Repeat/inputfile <port no.> <no. of pkts>
```

The inputfile should be in following format:

```
GBN
4 15
10000000
500
```

Where:

GBN/SR - Protocol Name\
4 - Bits used for Sequnce Number\
15 - Window Size\
10000000 - Timer in milliseconds\
500 - Max Segment Size








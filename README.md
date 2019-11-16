# network-protocols
Implementation of Go-Back-N, Selective repeat protocols

## Requirement:

You need python 2.7 version to run this code. To download python 2.7, please refer 

https://www.python.org/downloads/release/python-2712/

## Execution :

### Go-Back-N :
To start the Receiver, please run the following command 

```
python Go-Back-N/receiver.py 16000
```

To start the sender, please run the following commands

```
python Go-Back-N/sender.py Go-Back-N/inputfile 16000 100
```

### Selective Repeat

```
python Selective Repeat/receiver.py 16000
```

To start the sender, please run the following commands

```
python Selective Repeat/sender.py Selective Repeat/inputfile 16000 100
```

Where inputfile should be in following format :
GBN
4 15
10000000
500

GBN / SR - Protocol name
4 - Bits used for Sequnce number
15 - Window size
10000000 - timer in milliseconds
500 - max segment size

Argument 2 : 16000 - port number
Argument 3 : 100 - Number of packets to send









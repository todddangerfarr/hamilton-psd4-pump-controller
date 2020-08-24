# Testing
from functools import reduce


def string2bits(s=''):
    return [bin(ord(x))[2:].zfill(8) for x in s]


s = "\x0211ZR\x03\x09"
print(s)

binaries = string2bits("\x0211ZR\x03")

checksum = ''
for i in range(len(binaries[0])):
    val = 0
    for binary in binaries:
        val += int(binary[i])
    checksum += str(val % 2)
print(hex(int(checksum, 2)))


print(hex(reduce(lambda x, y: x ^ (ord(y)), "\x0211ZR\x03", 0)))

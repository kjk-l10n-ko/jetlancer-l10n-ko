"""List code references (reloc'd 32-bit immediates) inside the Japanese code branch that point at strings outside the Japanese slots (e.g. Chinese strings the JP branch reuses)."""
import struct, csv, sys
import numpy as np
b=open('backup/Jet Lancer.exe','rb').read()
BASE,DOFF,DVA=0x400000,0x10d6200,0x10d7000
pe=struct.unpack('<I',b[0x3c:0x40])[0]
ns=struct.unpack('<H',b[pe+6:pe+8])[0]; sec=pe+0x18+struct.unpack('<H',b[pe+0x14:pe+0x16])[0]
secs=[struct.unpack('<IIII',b[sec+i*40+8:sec+i*40+24]) for i in range(ns)]
rr=struct.unpack('<II',b[pe+0x18+0x60+5*8:pe+0x18+0x60+5*8+8])
def r2o(r):
    for vs,v,rs,ro in secs:
        if v<=r<v+rs: return ro+r-v
relocs=set(); o=r2o(rr[0]); end=o+rr[1]
while o<end:
    pg,sz=struct.unpack('<II',b[o:o+8])
    for k in range(8,sz,2):
        e=struct.unpack('<H',b[o+k:o+k+2])[0]
        if e>>12==3: relocs.add(r2o(pg+(e&0xfff)))
    o+=sz
TS,TE=17707584,17925000
lo,hi=BASE+DVA+TS-DOFF,BASE+DVA+TE-DOFF
rows=list(csv.reader(open('contents/ui_ko.tsv',encoding='utf-8'),delimiter='\t',quoting=csv.QUOTE_NONE))[1:]
jp={int(r[0]):r for r in rows}
refs=[(loc,v-(BASE+DVA)+DOFF) for loc in sorted(relocs) if 0<=loc<len(b)-4 for v in [struct.unpack('<I',b[loc:loc+4])[0]] if lo<=v<hi]
jprefs=[l for l,t in refs if t in jp]
print('refs total',len(refs),'jp refs',len(jprefs),'range',min(jprefs),max(jprefs))
def sat(t):
    s=b.rfind(b'\0',0,t+1)+1 if b[t-1:t]!=b'\0' else t
    e=b.find(b'\0',t); return b[t:e].decode('utf-8','replace')
out=[]
for l,t in refs:
    if min(jprefs)-300<=l<=max(jprefs)+300 and t not in jp:
        txt=sat(t)
        if any(ord(c)>127 for c in txt): out.append((l,t,txt))
for x in out: print(x)
print(len(out))
import collections
c=collections.Counter(t for l,t in refs if t in jp)
unused=[(t,jp[t][1],jp[t][2],int(jp[t][4])) for t in jp if c[t]==0]
print('JP slots with zero refs:',len(unused))
for u in unused: print(u)

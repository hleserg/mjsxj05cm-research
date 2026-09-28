import sys,struct
from elftools.elf.elffile import ELFFile
from capstone import *
p=sys.argv[1]; want=sys.argv[2:]
data=open(p,"rb").read(); e=ELFFile(open(p,"rb"))
segs=[(s['p_vaddr'],s['p_filesz'],s['p_offset']) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
def va2off(v):
    for a,z,o in segs:
        if a<=v<a+z: return v-a+o
def rd32(v):
    o=va2off(v); return struct.unpack("<I",data[o:o+4])[0] if o is not None else None
def cstr(v):
    o=va2off(v)
    if o is None: return None
    s=data[o:o+80].split(b"\0")[0]
    return s.decode("latin-1") if s and all(32<=c<127 for c in s) else None
syms=[]
for sec in (e.get_section_by_name(".dynsym"), e.get_section_by_name(".symtab")):
    if sec:
        for s in sec.iter_symbols():
            if s['st_info']['type'] in ('STT_FUNC','STT_OBJECT') and s['st_value']: syms.append((s['st_value']&~1,s['st_size'],s.name,s['st_info']['type']))
syms=sorted(set(syms)); addr2name={a:n for a,z,n,t in syms}
for w in want:
    if w.startswith('@'): a,_,b=w[1:].partition('-'); syms.append((int(a,0),(int(b,0)-int(a,0)) if b else 0x400,w,'STT_FUNC'))
if len(sys.argv)>2 and sys.argv[2]=='--rd32':
    for w in sys.argv[3:]: print(w, hex(rd32(int(w,0))))
    sys.exit()
plt={}; rel=e.get_section_by_name(".rel.plt"); dyn=e.get_section_by_name(".dynsym"); pltsec=e.get_section_by_name(".plt")
if rel and pltsec:
    for i,r in enumerate(rel.iter_relocations()): plt[pltsec['sh_addr']+20+12*i]=dyn.get_symbol(r['r_info_sym']).name
got={}
for secn in (".rel.dyn",):
    r=e.get_section_by_name(secn)
    if r:
        for x in r.iter_relocations():
            n=dyn.get_symbol(x['r_info_sym']).name
            if n: got[x['r_offset']]=n
md=Cs(CS_ARCH_ARM, CS_MODE_ARM); md.detail=True
for a,z,n,t in syms:
    if n not in want: continue
    if t=='STT_OBJECT':
        o=va2off(a); print(f"== OBJ {n} @ {a:#x} size {z}: {data[o:o+z].hex() if o is not None else '?'}"); continue
    print(f"== {n} @ {a:#x} size {z}")
    regs={}
    for i in md.disasm(data[va2off(a):va2off(a)+(z or 0x300)],a):
        s=f"  {i.address:#x}: {i.mnemonic} {i.op_str}"
        ops=i.op_str.replace(",","").split()
        if i.mnemonic=="ldr" and "[pc" in i.op_str:
            imm=int(ops[-1].strip("[]#"),0) if len(ops)>2 else 0
            lit=rd32(i.address+8+imm); regs[ops[0]]=lit; s+=f"   ; lit={lit:#x}"
        elif i.mnemonic=="add" and len(ops)==3 and ops[1]=="pc" and ops[2] in regs:
            v=(i.address+8+regs[ops[2]])&0xffffffff; regs[ops[0]]=v
            st=cstr(v); s+=f"   ; ={v:#x} {repr(st) if st else addr2name.get(v,'')}"
        elif i.mnemonic=="ldr" and len(ops)==3 and ops[1].startswith("[") and ops[1].strip("[]") in regs and ops[2].strip("[]#").lstrip("r").isdigit()==False:
            # ldr rX,[rBase, rIdx] GOT-relative
            base=regs.get(ops[1].strip("[]")); idx=regs.get(ops[2].strip("[]"))
            if base is not None and idx is not None:
                g=base+idx; s+=f"   ; GOT {g:#x} -> {got.get(g, addr2name.get(rd32(g) or -1,''))}"
        elif i.mnemonic in ("bl","blx","b"):
            try:
                tgt=int(ops[0].strip("#"),0); s+=f"   -> {plt.get(tgt) or addr2name.get(tgt,'')}"
            except: pass
        print(s)

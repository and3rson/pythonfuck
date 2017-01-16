#!/usr/bin/env python2

import os
import sys
from StringIO import StringIO
import subprocess
from tempfile import NamedTemporaryFile


HEADER = '''
section .text
global _start

read:
    push rdx
    mov eax, 0x03
    mov ebx, 0
    add edx, memory
    mov ecx, edx
    mov edx, 1
    int 0x80
    pop rdx
    ret

write:
    push rdx
    mov eax, 4
    mov ebx, 1
    mov ecx, memory
    add ecx, edx
    mov edx, 1
    int 0x80
    pop rdx
    ret

left:
    dec edx
    ret

right:
    inc edx
    ret

increase:
    push ax
    mov al, byte [memory + edx]
    inc al
    mov [memory + edx], al
    pop ax
    ret

decrease:
    push ax
    mov al, byte [memory + edx]
    dec al
    mov [memory + edx], al
    pop ax
    ret

_start:
    xor edx, edx
'''

FOOTER = '''
    mov eax, 1
    int 0x80

section .data
    buff db 0
    db 0
    memory times 256 db 0
'''


LOOP_START = '''
    mov ebx, edx
    add ebx, memory
    mov cl, byte [ebx]
    test cl, cl
    je {end_label}
'''


LOOP_END = '''
    mov ebx, edx
    add ebx, memory
    mov cl, byte [ebx]
    test cl, cl
    jne {start_label}
'''


def out(buff, instruction):
    buff.write('    {}\n'.format(instruction))


def out_label(buff, name):
    buff.write('{}:\n'.format(name))


def compile_asm(buff, exename):
    f = NamedTemporaryFile(suffix='.as', delete=False)
    f.write(buff)
    f.close()
    objfile = '{}.o'.format(f.name[:-3])

    ps = subprocess.Popen(['/usr/bin/nasm', '-f', 'elf64', f.name, '-o', objfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = ps.communicate()
    if ps.returncode:
        print out
        print err
        return sys.exit(1)
    ps = subprocess.Popen(['/usr/bin/ld', '-o', exename, objfile])
    out, err = ps.communicate()
    if ps.returncode:
        print out
        print err
        return sys.exit(1)
    os.unlink(f.name)


def main(filename):
    buff = StringIO()

    f = open(filename)
    buff.write(HEADER)
    code = f.read()

    last_loop_id = 1
    loop_stack = []

    for c in code:
        if c in ('\n', ' ', '\t'):
            continue

        if c == '+':
            out(buff, 'call increase')
        elif c == '-':
            out(buff, 'call decrease')
        elif c == '<':
            out(buff, 'call left')
        elif c == '>':
            out(buff, 'call right')
        elif c == ',':
            out(buff, 'call read')
        elif c == '.':
            out(buff, 'call write')
        elif c == '[':
            start_label = 'loop_{}'.format(last_loop_id)
            end_label = 'loop_{}_end'.format(last_loop_id)

            last_loop_id += 1
            loop_stack.append((start_label, end_label))

            buff.write(LOOP_START.format(end_label=end_label))
            out_label(buff, start_label)
        elif c == ']':
            start_label, end_label = loop_stack.pop()
            buff.write(LOOP_END.format(start_label=start_label))
            out_label(buff, end_label)

    f.close()
    buff.write(FOOTER)

    name, _, ext = filename.rpartition('.')
    exename = '{}.bin'.format(name)

    compile_asm(buff.getvalue(), exename)


if __name__ == '__main__':
    main(sys.argv[1])

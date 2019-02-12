#!/usr/bin/env python3

"""Try to convert LaTeX in titles/abstracts into Unicode and/or math inside <tex-math>...</tex-math>.

Usage: python3 latex_to_unicode.py <infile> -o <outfile> -f title -f abstract

Bugs: Doesn't preserve line breaks and indentation.
"""

import xml.etree.ElementTree
import re
import codecs, latexcodec

math_re = re.compile(r'\$([^\$]*)\$', re.MULTILINE)

def detex(s):
    if s is None: return None
    
    # We don't actually know whether the string is in TeX. If it has a
    # bare %, latexcodec treats it as a comment delimiter. Assuming
    # that titles/abstracts don't have comments in them, we escape %
    # so it is treated as percent, not a comment delimiter.
    s = re.sub(r'(?<!\\)%', r'\%', s)

    # Convert special characters
    # bug (in latexcodec): doesn't handle ``a+b'' correctly
    # bug: doesn't convert single quotes
    s = codecs.decode(s, "ulatex+utf8")

    # Remove soft hyphen
    s = s.replace('\xad', '')

    return s

def detex_node(node):
    if node is None: return None
    
    newnode = xml.etree.ElementTree.Element(node.tag, node.attrib)

    def append_text(text):
        if len(newnode) == 0:
            newnode.text = text
        else:
            newnode[-1].tail = text

    def append_math(text):
        if text is None: return
        prev = 0
        for m in math_re.finditer(text):
            append_text(text[prev:m.start()])
            tex = xml.etree.ElementTree.Element('tex-math')
            tex.text = m.group(1)
            newnode.append(tex)
            prev = m.end()
        append_text(text[prev:])
    
    append_math(detex(node.text))
    for child in node:
        newnode.append(detex_node(child))
        append_math(detex(child.tail))
    newnode.tail = node.tail

    return newnode

def node_tostring(node):
    if node is None: return ""
    s = xml.etree.ElementTree.tostring(node, encoding='utf8').decode('utf8')
    _, s = s.split('\n', 1) # remove declaration
    return ' '.join(s.split())

if __name__ == "__main__":
    import sys
    import argparse
    ap = argparse.ArgumentParser(description='Convert LaTeX commands and special characters.')
    ap.add_argument('infile', help="XML file to convert")
    ap.add_argument('-o', dest='outfile', help="XML file to write (default stdout)")
    ap.add_argument('-f', '--field', action='append', help="Field to convert (can be used more than once)")
    args = ap.parse_args()
    if not args.field:
        print("error: at least one field (-f) is required", file=sys.stderr)
        sys.exit(1)
    if not args.outfile:
        print("error: output file (-o) is required", file=sys.stderr)
        sys.exit(1)

    tree = xml.etree.ElementTree.parse(args.infile)
    root = tree.getroot()
    for paper in root.findall('paper'):
        for field in args.field:
            node = paper.find(field)
            newnode = detex_node(node)
            orig = node_tostring(node)
            mod = node_tostring(newnode)
            if orig != mod:
                print("{}-{}: {} -> {}".format(root.attrib['id'], paper.attrib['id'], orig, mod), file=sys.stderr)
                # replace new with newnode; isn't there an easier way?
                node.clear()
                node.attrib = newnode.attrib
                node.text = newnode.text
                node.tail = newnode.tail
                node.extend(newnode)

    tree.write(args.outfile, encoding="UTF-8")

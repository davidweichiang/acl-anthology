#!/usr/bin/env python3

"""Try to convert LaTeX in titles/abstracts into Unicode and/or math inside <tex-math>...</tex-math>.

Usage: python3 latex_to_unicode.py <infile> -o <outfile> -f title -f abstract

Bugs: Doesn't preserve line breaks and indentation.
"""

import xml.etree.ElementTree
import re
import codecs, latexcodec

math_re = re.compile(r'\$([^\$]*)\$', re.MULTILINE)

def replace_node(old, new):
    old.clear()
    old.tag = new.tag
    old.attrib = new.attrib
    old.text = new.text
    old.extend(new)
    old.tail = new.tail

def append_text(node, text):
    if len(node) == 0:
        if node.text is None:
            node.text = ""
        node.text += text
    else:
        if node[-1].tail is None:
            node[-1].tail = ""
        node[-1].tail += text

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

    def append_math(text):
        if text is None: return
        prev = 0
        for m in math_re.finditer(text):
            append_text(newnode, text[prev:m.start()])
            tex = xml.etree.ElementTree.Element('tex-math')
            tex.text = m.group(1)
            newnode.append(tex)
            prev = m.end()
        append_text(newnode, text[prev:])
    
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
    ap.add_argument('infile', help="XML file to read")
    ap.add_argument('outfile', help="XML file to write")
    ap.add_argument('-f', '--field', action='append', help="Field to convert (can be used more than once)")
    args = ap.parse_args()
    if not args.field:
        print("error: at least one field (-f) is required", file=sys.stderr)
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
                replace_node(node, newnode)

    tree.write(args.outfile, encoding="UTF-8")

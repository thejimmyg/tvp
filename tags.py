# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

def escape(s, quote=True):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true (the default), the quotation mark
    characters, both double quote (") and single quote (') characters are also
    translated.
    """
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace('\'', "&#x27;")
    return s


class TemplateTag:
    def __init__(self, *k):
        assert len(k)
        if len(k) == 1:
            if type(k[0]) is str:
                self.name = k[0]
                self.attrs = None
                self.children = None
            else:
                assert type(k[0]) is not dict
                self.name = None
                self.children = k[0]
                self.attrs = None
        else:
            assert len(k) >= 2
            self.name = k[0]
            self.attrs = k[1]
            if len(k) > 2:
                self.children = k[2]
            else:
                self.children = None

tag = TemplateTag

class Placeholder:
    def __init__(self, name):
        self.name = name
        self.indent = ''

def render_attrs(attrs):
    all = []
    for key, value in attrs.items():
        if value is True:
            all.append(' ' + escape(key))
        elif value is False or value is None:
            pass
        else:
            all.append(f' {escape(key)}="{escape(value)}"')
    return ''.join(all)

def tag2template(t, indent='', parts=None, placeholders=None):
    if parts is None:
        parts = ['']
    if placeholders is None:
        placeholders = []
    if t.name is None:
        if type(t.children) is list:
            if len(t.children) == 1 and type(t.children[0]) is str:
                parts[-1] += escape(t.children[0])
            else:
                extra_indent = '  '
                if t.name == 'html':
                    extra_indent = ''
                for item in t.children:
                    if type(item) is TemplateTag:
                        child_parts, child_placeholders = tag2template(item, indent=indent + extra_indent)
                        parts[-1] += '\n' + child_parts[0]
                        parts += child_parts[1:]
                        placeholders += child_placeholders
                    elif type(item) is str:
                        parts[-1] += '\n' + indent + extra_indent + escape(item)
                    elif type(item) is Placeholder:
                        parts[-1] += '\n'#  + indent + extra_indent
                        placeholders.append((escape(item.name), indent + extra_indent, True))
                        parts.append('')
                    else:
                        raise ValueError('Unexpected: '+repr(item))

        elif type(t.children) is str:
            parts[-1] += escape(t.children)
        elif type(t.children) is Placeholder:
            placeholders.append((escape(t.children.name), indent, False))
        else:
            raise ValueError('Unexpected: ' + repr(t.children))
    else:
        escaped_name = escape(t.name)
        if t.attrs:
            parts[-1] += indent+'<' + escaped_name + render_attrs(t.attrs) + '>'
        else:
            parts[-1] += indent+'<' + escaped_name + '>'
        if t.children is not None:
            if type(t.children) is list:
                if len(t.children) == 1 and type(t.children[0]) is str:
                    parts[-1] += escape(t.children[0]) + '</' + escaped_name + '>'
                else:
                    extra_indent = '  '
                    if t.name == 'html':
                        extra_indent = ''
                    for item in t.children:
                        if type(item) is TemplateTag:
                            child_parts, child_placeholders = tag2template(item, indent=indent + extra_indent)
                            parts[-1] += '\n' + child_parts[0]
                            parts += child_parts[1:]
                            placeholders += child_placeholders
                        elif type(item) is str:
                            parts[-1] +=  indent + extra_indent + escape(item)
                        elif type(item) is Placeholder:
                            parts[-1] += '\n'#  + indent + extra_indent
                            placeholders.append((escape(item.name), indent + extra_indent, True))
                            parts.append('')
                        else:
                            raise ValueError('Unexpected: '+repr(item))
                    parts[-1] += '\n' + indent+'</' + escaped_name + '>'
            elif type(t.children) is str:
                parts[-1] += escape(t.children) + '</' + escaped_name + '>'
            elif type(t.children) is Placeholder:
                placeholders.append((escape(t.children.name), indent, False))
                parts.append('</' + escaped_name + '>')
            else:
                raise ValueError('Unexpected: ' + repr(t.children))
    return parts, placeholders

def tag2html(t, indent=''):
    parts, placeholders = tag2template(t, indent)
    assert placeholders == []
    return parts[0]

def render_template(template, values=None):
    if values is None:
        values = {}
    result = ''
    parts, placeholders = template
    result += parts[0]
    for i, part in enumerate(parts[1:]):
        block = values[placeholders[i][0]]
        if type(block) is TemplateTag:
            # Indent the whole block
            result += tag2html(block, indent=placeholders[i][1]) + part
        elif placeholders[i][2]:
            # This is a part of a child list, so indent it
            result += placeholders[i][1] + values[placeholders[i][0]] + part
        else:
            # This is a standalone child, don't indent it
            result += values[placeholders[i][0]] + part
    return result

class Template:
    def __init__(self, tree):
         self.template = tag2template(tree)

    def render(self, **values):
         return render_template(self.template, values)


if __name__ == '__main__':
    import time

    def nav(links):
        return tag('ul', {}, [
           tag('li', {}, [
               tag('a', {'href': link}, text)
           ]) for link, text in links
        ])

    page = Template(
        tag('html', {'lang': 'en'}, [
            tag('head', {}, [
                tag('title', {}, Placeholder('title')),
                tag('meta', {'name': "viewport", 'content': "width=device-width, initial-scale=1.0"}),
                tag('meta', {'charset': "UTF-8"}),
            ]),
            tag('body', {}, [
                tag('div', {}, [
                    tag('h1', {}, Placeholder('title')),
                    tag('span', {}, [Placeholder('title')]),
                    Placeholder('body'),
                ])
            ])
        ])
    )

    def run():
        return page.render(
            title='This is the title',
            body=nav([
                ('/html', 'HTML'),
                ('/str', 'str'),
                ('/dict', 'dict'),
                ('/bytes', 'bytes'),
                ('/other', 'Other (should raise error)'),
            ])
        )

    print(page.template)
    print(run())
    number = 5000

    start = time.time()
    for _ in range(number):
        run()
    print(number / (time.time() - start))

    print(tag2html(tag([
        'Hi',
        tag('br', {}),
        'World'
    ])))

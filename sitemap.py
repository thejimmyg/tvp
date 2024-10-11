# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

from tags import tag


class Page:
    def __init__(self, title, path, children=None, section=None, parent_page=None):
        self.title = title
        self.path = path
        self.children = children if children is not None else []
        self.section = section
        self.parent_page = parent_page

    def set_parents(self, section, parent_page=None):
        self.section = section
        self.parent_page = parent_page

    def __repr__(self):
        return f"Page(title='{self.title}', path='{self.path}')"


class Section:
    def __init__(self, title, children=None, parent=None):
        self.title = title
        self.children = children if children is not None else []
        self.parent = parent
        self.path = None

    def set_parent(self, parent):
        self.parent = parent

    def __repr__(self):
        return f"Section(title='{self.title}', path='{self.path}')"


def extract_hierarchy(nav, parent=None, section_index=None, page_index=None, parent_page=None):
    if section_index is None:
        section_index = {}
    if page_index is None:
        page_index = {}

    # If this is a section, set the parent and determine the path
    if isinstance(nav, Section):
        nav.set_parent(parent)

        # Find the first child page's path to set as the section's path
        first_page = next((child for child in nav.children if isinstance(child, Page)), None)
        if first_page:
            nav.path = first_page.path
            section_index[nav.path] = nav

        # Recurse for children, passing the current section as parent
        for child in nav.children:
            extract_hierarchy(child, nav, section_index, page_index)

    elif isinstance(nav, Page):
        # Set parent section and parent page (if any)
        nav.set_parents(parent, parent_page)

        # Add the page to the page index
        page_index[nav.path] = nav

        # Recurse for children in a page (if any)
        if nav.children:
            for child in nav.children:
                extract_hierarchy(child, parent, section_index, page_index, nav)

    return section_index, page_index


def breadcrumbs(page_index, path):
    # Start by getting the section for the current page from the page_index
    section = page_index[path].section
    if section.parent is None:
        return tag([])
    breadcrumbs_list = [[section.title, section.path, False]]  # Collect the current section
    # Traverse the parent section hierarchy upwards
    while section.parent is not None:
        section = section.parent
        breadcrumbs_list.append([section.title, section.path, False])  # Append each parent section
    for breadcrumb in breadcrumbs_list:
        if path != breadcrumb[1]:
            breadcrumb[2] = True
            break
    # Generate the <ul> with <li> and <a> tags for breadcrumbs
    return tag('ul', {'class': 'breadcrumbs'}, [
        tag('li', {'class': is_parent_link and 'is_parent_link' or None}, [
            path == breadcrumb_path and tag('span', {}, title) or tag('a', {'href': breadcrumb_path}, title)
        ]) for title, breadcrumb_path, is_parent_link in reversed(breadcrumbs_list)  # Reverse to get correct order
    ])


def main_nav(nav, path):
    # Assume the top-level section is the first in nav's children
    return tag('ul', {'class': 'main_nav'}, [
        tag('li', {}, [
            path == page_or_section.path and tag('span', {}, page_or_section.title) or tag('a', {'href': page_or_section.path}, page_or_section.title)
        ]) for page_or_section in nav.children
    ])


def section_nav(page_index, path):
    # Recursively build the tag tree for pages and sections
    section = page_index[path].section
    if section.parent is None:
        return tag([])
    def recurse_children(container_tag, node):
        for child in node.children:
            li = tag('li', isinstance(child, Section) and  {'class': 'section'} or {}, [
                child.path == path and tag('span', {}, child.title) or tag('a', {'href': child.path}, child.title)
            ])
            container_tag.children.append(li)
            if isinstance(child, Page) and child.children:
                new_container_tag = tag('ul', {}, [])
                container_tag.children.append(new_container_tag)
                recurse_children(new_container_tag, child)

    section = page_index.get(path).section
    container_tag = tag('ul', {'class': 'section_nav'}, [])
    recurse_children(container_tag, section)
    return container_tag



class PageNav:
    def __init__(self, nav, page_index, section_index, path):
        self.nav = nav
        self.page_index = page_index
        self.section_index = section_index
        self.path = path

    def breadcrumbs(self):
        if self.path not in self.page_index:
            return ''
        return breadcrumbs(self.page_index, self.path)

    def section_nav(self):
        if self.path not in self.page_index:
            return ''
        return section_nav(self.page_index, self.path)

    def main_nav(self):
        if self.path not in self.page_index:
            return ''
        return main_nav(self.nav, self.path)


class NavMiddleware:
    def __init__(self, app, nav):
        self.app = app
        self.nav = nav
        self.section_index, self.page_index = extract_hierarchy(nav)
        print(self.page_index)

    async def __call__(self, scope, receive, send):
        assert 'nav' not in scope
        scope['nav'] = PageNav(self.nav, self.page_index, self.section_index, scope['path'])
        await self.app(scope, receive, send)


if __name__ == '__main__':
    from tags import tag2html


    nav = Section('Home', [
        Page('Home', '/'),
        Page('Main', '/main'),
        Section('About', [
            Page('About', '/about', [
                Page('Details', '/about/details'),
            ])
        ])
    ])

    section_index, page_index = extract_hierarchy(nav)

    print("Section hierarchy with parent info:")
    for path, section in section_index.items():
        print(f"Section: {section.title}, Path: {section.path}, Parent: {section.parent.title if section.parent else 'None'}")

    print("\nPage index with parent section and parent page info:")
    for path, page in page_index.items():
        section_title = page.section.title if page.section else 'None'
        parent_page_title = page.parent_page.title if page.parent_page else 'None'
        print(f"Page: {page.title}, Path: {page.path}, Parent Section: {section_title}, Parent Page: {parent_page_title}")

    print("\nBreadcrumbs:")
    print(tag2html(breadcrumbs(page_index, '/about/details')))

    print("\nMain Navigation HTML:")
    print(tag2html(main_nav(nav, '/')))
    print(tag2html(main_nav(nav, '/about')))

    print("\nSection nav:")
    print('/about')
    print(tag2html(section_nav(page_index, '/about')))
    print('/')
    print(tag2html(section_nav(page_index, '/')))

#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Richard Hughes <richard@hughsie.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA

import sys
import xml.etree.ElementTree as ET
import dateutil.parser
from datetime import datetime

try:
    # Py2.7 and newer
    from xml.etree.ElementTree import ParseError as StdlibParseError
except ImportError:
    # Py2.6 and older
    from xml.parsers.expat import ExpatError as StdlibParseError

from appstream.errors import ParseError, ValidationError
from appstream.utils import _join_lines, _parse_desc

if sys.version_info[0] == 2:
    # Python2 has a nice basestring base class
    string_types = (basestring,)
else:
    # But python3 has distinct types
    string_types = (str, bytes)

class Checksum(object):
    def __init__(self):
        """ Set defaults """
        self.kind = 'sha1'
        self.target = None
        self.value = None
        self.filename = None
    def to_xml(self):
        return '        <checksum filename="%s" target="%s" type="sha1">%s</checksum>\n' % (self.filename, self.target, self.value)
    def _parse_tree(self, node):
        """ Parse a <checksum> object """
        if 'filename' in node.attrib:
            self.filename = node.attrib['filename']
        if 'type' in node.attrib:
            self.kind = node.attrib['type']
        if 'target' in node.attrib:
            self.target = node.attrib['target']
        self.value = node.text

class Review(object):
    def __init__(self):
        """ Set defaults """
        self.id = None
        self.summary = None
        self.description = None
        self.locale = None
        self.karma = 0
        self.score = 0
        self.rating = 0
        self.version = None
        self.reviewer_id = None
        self.reviewer_name = None
        self.date = None
        self.metadata = {}

    def _parse_tree(self, node):
        """ Parse a <review> object """
        if 'date' in node.attrib:
            dt = dateutil.parser.parse(node.attrib['date'])
            self.date = int(dt.strftime("%s"))
        if 'id' in node.attrib:
            self.id = node.attrib['id']
        if 'karma' in node.attrib:
            self.karma = int(node.attrib['karma'])
        if 'score' in node.attrib:
            self.score = int(node.attrib['score'])
        if 'rating' in node.attrib:
            self.rating = int(node.attrib['rating'])
        for c3 in node:
            if c3.tag == 'lang':
                self.locale = c3.text
            if c3.tag == 'version':
                self.version = c3.text
            if c3.tag == 'reviewer_id':
                self.reviewer_id = c3.text
            if c3.tag == 'reviewer_name':
                self.reviewer_name = c3.text
            if c3.tag == 'summary':
                self.summary = c3.text
            if c3.tag == 'description':
                self.description = _parse_desc(c3)
            if c3.tag == 'metadata':
                for c4 in c3:
                    if c4.tag == 'value':
                        if 'key' in c4.attrib:
                            self.metadata[c4.attrib['key']] = c4.text

    def to_xml(self):
        xml = '      <review'
        if self.date:
            xml += ' date="%s"' % datetime.fromtimestamp(self.date).isoformat()
        if self.rating:
            xml += ' rating="%s"' % self.rating
        if self.score:
            xml += ' score="%i"' % self.score
        if self.karma:
            xml += ' karma="%s"' % self.karma
        if self.id:
            xml += ' id="%s"' % self.id
        xml += '>\n'
        if self.summary:
            xml += '        <summary>%s</summary>\n' % self.summary
        if self.description:
            xml += '        <description>%s</description>\n' % self.description
        if self.version:
            xml += '        <version>%s</version>\n' % self.version
        if self.reviewer_id:
            xml += '        <reviewer_id>%s</reviewer_id>\n' % self.reviewer_id
        if self.reviewer_name:
            xml += '        <reviewer_name>%s</reviewer_name>\n' % self.reviewer_name
        if self.locale:
            xml += '        <lang>%s</lang>\n' % self.locale
        if len(self.metadata) > 0:
            xml += '        <metadata>\n'
            for key in self.metadata:
                xml += '          <value key=\"%s\">%s</value>\n' % (key, self.metadata[key])
            xml += '        </metadata>\n'
        xml += '      </review>\n'
        return xml

class Release(object):
    def __init__(self):
        """ Set defaults """
        self.version = None
        self.description = None
        self.timestamp = 0
        self.checksums = []
        self.location = None
        self.size_installed = 0
        self.size_download = 0
        self.urgency = None

    def get_checksum_by_target(self, target):
        """ returns a checksum of a specific kind """
        for csum in self.checksums:
            if csum.target == target:
                return csum
        return None

    def add_checksum(self, csum):
        """ Add a checksum to a release object """
        for csum_tmp in self.checksums:
            if csum_tmp.target == csum.target:
                self.checksums.remove(csum_tmp)
                break
        self.checksums.append(csum)

    def _parse_tree(self, node):
        """ Parse a <release> object """
        if 'timestamp' in node.attrib:
            self.timestamp = int(node.attrib['timestamp'])
        if 'date' in node.attrib:
            dt = dateutil.parser.parse(node.attrib['date'])
            self.timestamp = int(dt.strftime("%s"))
        if 'urgency' in node.attrib:
            self.urgency = node.attrib['urgency']
        if 'version' in node.attrib:
            self.version = node.attrib['version']
            # fix up hex value
            if self.version.startswith('0x'):
                self.version = str(int(self.version[2:], 16))
        for c3 in node:
            if c3.tag == 'description':
                self.description = _parse_desc(c3)
            if c3.tag == 'size':
                if 'type' not in c3.attrib:
                    continue
                if c3.attrib['type'] == 'installed':
                    self.size_installed = int(c3.text)
                if c3.attrib['type'] == 'download':
                    self.size_download = int(c3.text)
            elif c3.tag == 'checksum':
                csum = Checksum()
                csum._parse_tree(c3)
                self.add_checksum(csum)

    def to_xml(self):
        xml = '      <release'
        if self.version:
            xml += ' version="%s"' % self.version
        if self.timestamp:
            xml += ' timestamp="%i"' % self.timestamp
        if self.urgency:
            xml += ' urgency="%s"' % self.urgency
        xml += '>\n'
        if self.size_installed > 0:
            xml += '        <size type="installed">%i</size>\n' % self.size_installed
        if self.size_download > 0:
            xml += '        <size type="download">%i</size>\n' % self.size_download
        if self.location:
            xml += '        <location>%s</location>\n' % self.location
        for csum in self.checksums:
            xml += csum.to_xml()
        if self.description:
            xml += '        <description>%s</description>\n' % self.description
        xml += '      </release>\n'
        return xml

class Image(object):
    def __init__(self):
        """ Set defaults """
        self.kind = None
        self.width = 0
        self.height = 0
        self.url = None

    def to_xml(self):
        xml = '        <image'
        if self.kind:
            xml += ' type="%s"' % self.kind
        if self.width > 0:
            xml += ' width="%i"' % self.width
        if self.height > 0:
            xml += ' height="%i"' % self.height
        xml += '>'
        if self.url:
            xml += self.url
        xml += '</image>\n'
        return xml

    def _parse_tree(self, node):
        """ Parse a <image> object """
        if 'type' in node.attrib:
            self.kind = node.attrib['type']
        if 'width' in node.attrib:
            self.width = int(node.attrib['width'])
        if 'height' in node.attrib:
            self.height = int(node.attrib['height'])
        self.url = node.text

class Screenshot(object):
    def __init__(self):
        """ Set defaults """
        self.kind = None
        self.caption = None
        self.images = []

    def get_image_by_kind(self, kind):
        """ returns a image of a specific kind """
        for ss in self.images:
            if ss.kind == kind:
                return ss
        return None

    def add_image(self, im):
        """ Add a image to a screenshot object """
        for im_tmp in self.images:
            if im_tmp.kind == im.kind:
                self.images.remove(im_tmp)
                break
        self.images.append(im)

    def _parse_tree(self, node):
        """ Parse a <screenshot> object """
        if 'type' in node.attrib:
            self.kind = node.attrib['type']
        for c3 in node:
            if c3.tag == 'caption':
                self.caption = _parse_desc(c3)
            elif c3.tag == 'image':
                im = Image()
                im._parse_tree(c3)
                self.add_image(im)

    def to_xml(self):
        xml = '      <screenshot'
        if self.kind:
            xml += ' type="%s"' % self.kind
        xml += '>\n'
        for im in self.images:
            xml += im.to_xml()
        if self.caption:
            xml += '        <caption>%s</caption>\n' % self.caption
        xml += '      </screenshot>\n'
        return xml

class Provide(object):
    def __init__(self):
        """ Set defaults """
        self.kind = None
        self.value = None
    def _parse_tree(self, node):
        """ Parse a <provide> object """
        if node.tag == 'firmware':
            if 'type' in node.attrib and node.attrib['type'] == 'flashed':
                self.kind = 'firmware-flashed'
            self.value = node.text.lower()

class Require(object):
    def __init__(self):
        """ Set defaults """
        self.kind = None
        self.compare = None
        self.version = None
        self.value = None
    def _parse_tree(self, node):
        """ Parse a <require> object """
        self.kind = node.tag
        if 'compare' in node.attrib:
            self.compare = node.attrib['compare']
        if 'version' in node.attrib:
            self.version = node.attrib['version']
        self.value = node.text

class Component(object):
    """ A quick'n'dirty MetaInfo parser """

    def __init__(self):
        """ Set defaults """
        self.id = None
        self.update_contact = None
        self.kind = None
        self.provides = []
        self.requires = []
        self.name = None
        self.pkgname = None
        self.summary = None
        self.description = None
        self.urls = {}
        self.icons = {}
        self.metadata_license = None
        self.project_license = None
        self.developer_name = None
        self.releases = []
        self.reviews = []
        self.screenshots = []
        self.kudos = []
        self.keywords = []
        self.categories = []
        self.custom = {}
        self.bundle = {}

    def to_xml(self):
        xml = '  <component type="firmware">\n'
        if self.id:
            xml += '    <id>%s</id>\n' % self.id
        if self.pkgname:
            xml += '    <pkgname>%s</pkgname>\n' % self.pkgname
        if self.name:
            xml += '    <name>%s</name>\n' % self.name
        if self.summary:
            xml += '    <summary>%s</summary>\n' % self.summary
        if self.developer_name:
            xml += '    <developer_name>%s</developer_name>\n' % self.developer_name
        if self.project_license:
            xml += '    <project_license>%s</project_license>\n' % self.project_license
        if self.description:
            xml += '    <description>%s</description>\n' % self.description
        if self.bundle:
            xml += '    <bundle type="%(type)" %(runtime) %(sdk)>%(value)</bundle>\n' % \
                   {
                       'type': self.bundle['type'],
                       'runtime': ('runtime="%s"' % self.bundle['runtime']) if self.bundle['runtime'] != 'unknown' else "",
                       'sdk': ('sdk="%s"' % self.bundle['sdk']) if self.bundle['sdk'] != 'unknown' else "",
                       'value': self.bundle['value']
                   }
        for key in self.urls:
            xml += '    <url type="%s">%s</url>\n' % (key, self.urls[key])
        for key in self.icons:
            xml += '    <icon type="%s">%s</icon>\n' % (key, self.icons[key]['value'])
        if len(self.releases) > 0:
            xml += '    <releases>\n'
            for rel in self.releases:
                xml += rel.to_xml()
            xml += '    </releases>\n'
        if len(self.reviews) > 0:
            xml += '    <reviews>\n'
            for rel in self.reviews:
                xml += rel.to_xml()
            xml += '    </reviews>\n'
        if len(self.screenshots) > 0:
            xml += '    <screenshots>\n'
            for rel in self.screenshots:
                xml += rel.to_xml()
            xml += '    </screenshots>\n'
        if len(self.kudos) > 0:
            xml += '    <kudos>\n'
            for kudo in self.kudos:
                xml += '      <kudo>%s</kudo>\n' % kudo
            xml += '    </kudos>\n'
        if len(self.keywords) > 0:
            xml += '    <keywords>\n'
            for keyword in self.keywords:
                xml += '      <keyword>%s</keyword>\n' % keyword
            xml += '    </keywords>\n'
        if len(self.categories) > 0:
            xml += '    <categories>\n'
            for category in self.categories:
                xml += '      <category>%s</category>\n' % category
            xml += '    </categories>\n'
        if len(self.provides) > 0:
            xml += '    <provides>\n'
            for p in self.provides:
                xml += '      <firmware type="flashed">%s</firmware>\n' % p.value
            xml += '    </provides>\n'
        if len(self.requires) > 0:
            xml += '    <requires>\n'
            for p in self.requires:
                if not p.kind:
                    continue
                xml += '      <%s' % p.kind
                if p.compare:
                    xml += ' compare="%s"' % p.compare
                if p.version:
                    xml += ' version="%s"' % p.version
                xml += '>'
                if p.value:
                    xml += p.value
                xml += '</%s>\n' % p.kind
            xml += '    </requires>\n'
        if len(self.custom) > 0:
            xml += '    <custom>\n'
            for key in self.custom:
                xml += '      <value key="%s">%s</value>\n' % (key, self.custom[key])
            xml += '    </custom>\n'
        xml += '  </component>\n'
        return xml

    def add_release(self, release):
        """ Add a release object if it does not already exist """
        for r in self.releases:
            if r.version == release.version:
                return
        self.releases.append(release)

    def add_review(self, review):
        """ Add a release object if it does not already exist """
        for r in self.reviews:
            if r.id == review.id:
                return
        self.reviews.append(review)

    def add_screenshot(self, screenshot):
        """ Add a screenshot object if it does not already exist """
        if screenshot in self.screenshots:
            return
        self.screenshots.append(screenshot)

    def add_provide(self, provide):
        """ Add a provide object if it does not already exist """
        for p in self.provides:
            if p.value == provide.value:
                return
        self.provides.append(provide)

    def get_provides_by_kind(self, kind):
        """ Returns an array of provides of a certain kind """
        provs = []
        for p in self.provides:
            if p.kind == kind:
                provs.append(p)
        return provs

    def add_require(self, require):
        """ Add a require object if it does not already exist """
        for p in self.requires:
            if p.value == require.value:
                return
        self.requires.append(require)

    def get_require_by_kind(self, kind, value):
        """ Returns a requires object of a specific value """
        for r in self.requires:
            if r.kind == kind and r.value == value:
                return r
        return None

    def validate(self):
        """ Parse XML data """
        if not self.id or len(self.id) == 0:
            raise ValidationError('No <id> tag')
        if not self.name or len(self.name) == 0:
            raise ValidationError('No <name> tag')
        if not self.summary or len(self.summary) == 0:
            raise ValidationError('No <summary> tag')
        if not self.description or len(self.description) == 0:
            raise ValidationError('No <description> tag')
        if self.kind == 'firmware':
            if len(self.provides) == 0:
                raise ValidationError('No <provides> tag')
            if len(self.releases) == 0:
                raise ValidationError('No <release> tag')
        if self.kind == 'desktop':
            if len(self.screenshots) == 0:
                raise ValidationError('No <screenshot> tag')
        if not self.metadata_license or len(self.metadata_license) == 0:
            raise ValidationError('No <metadata_license> tag')
        valid_licenses = [
            'CC0-1.0',
            'CC-BY-3.0',
            'CC-BY-4.0',
            'CC-BY-SA-3.0',
            'CC-BY-SA-4.0',
            'GFDL-1.1',
            'GFDL-1.2',
            'GFDL-1.3',
            'FSFAP'
        ]
        if self.metadata_license not in valid_licenses:
            raise ValidationError('Invalid <metadata_license> tag')
        if not self.project_license or len(self.project_license) == 0:
            raise ValidationError('No <project_license> tag')
        if not self.developer_name or len(self.developer_name) == 0:
            raise ValidationError('No <developer_name> tag')

        # verify release objects
        for rel in self.releases:
            if not rel.version or len(rel.version) == 0:
                raise ValidationError('No version in <release> tag')
            if rel.timestamp == 0:
                raise ValidationError('No timestamp in <release> tag')

    def parse(self, xml_data):
        """ Parse XML data """

        # parse tree
        if isinstance(xml_data, string_types):
            # Presumably, this is textual xml data.
            try:
                root = ET.fromstring(xml_data)
            except StdlibParseError as e:
                raise ParseError(str(e))
        else:
            # Otherwise, assume it has already been parsed into a tree
            root = xml_data

        # get type
        if 'type' in root.attrib:
            self.kind = root.attrib['type']

        # parse component
        for c1 in root:

            # <id>
            if c1.tag == 'id':
                self.id = c1.text

            # <updatecontact>
            elif c1.tag == 'updatecontact' or c1.tag == 'update_contact':
                self.update_contact = c1.text

            # <metadata_license>
            elif c1.tag == 'metadata_license':
                self.metadata_license = c1.text

            # <releases>
            elif c1.tag == 'releases':
                for c2 in c1:
                    if c2.tag == 'release':
                        rel = Release()
                        rel._parse_tree(c2)
                        self.add_release(rel)

            # <reviews>
            elif c1.tag == 'reviews':
                for c2 in c1:
                    if c2.tag == 'review':
                        rev = Review()
                        rev._parse_tree(c2)
                        self.add_review(rev)

            # <screenshots>
            elif c1.tag == 'screenshots':
                for c2 in c1:
                    if c2.tag == 'screenshot':
                        ss = Screenshot()
                        ss._parse_tree(c2)
                        self.add_screenshot(ss)

            # <provides>
            elif c1.tag == 'provides':
                for c2 in c1:
                    prov = Provide()
                    prov._parse_tree(c2)
                    self.add_provide(prov)

            # <requires>
            elif c1.tag == 'requires':
                for c2 in c1:
                    req = Require()
                    req._parse_tree(c2)
                    self.add_require(req)

            # <kudos>
            elif c1.tag == 'kudos':
                for c2 in c1:
                    if not c2.tag == 'kudo':
                        continue
                    self.kudos.append(c2.text)

            # <keywords>
            elif c1.tag == 'keywords':
                for c2 in c1:
                    if not c2.tag == 'keyword':
                        continue
                    self.keywords.append(c2.text)

            # <categories>
            elif c1.tag == 'categories':
                for c2 in c1:
                    if not c2.tag == 'category':
                        continue
                    self.categories.append(c2.text)

            # <custom>
            elif c1.tag == 'custom':
                for c2 in c1:
                    if not c2.tag == 'value':
                        continue
                    if 'key' not in c2.attrib:
                        continue
                    self.custom[c2.attrib['key']] = c2.text

            # <project_license>
            elif c1.tag == 'project_license' or c1.tag == 'licence':
                self.project_license = c1.text

            # <developer_name>
            elif c1.tag == 'developer_name':
                self.developer_name = _join_lines(c1.text)

            # <name>
            elif c1.tag == 'name' and not self.name:
                self.name = _join_lines(c1.text)

            # <pkgname>
            elif c1.tag == 'pkgname' and not self.pkgname:
                self.pkgname = _join_lines(c1.text)

            # <summary>
            elif c1.tag == 'summary' and not self.summary:
                self.summary = _join_lines(c1.text)

            # <description>
            elif c1.tag == 'description' and not self.description:
                self.description = _parse_desc(c1)

            # <url>
            elif c1.tag == 'url':
                key = 'homepage'
                if 'type' in c1.attrib:
                    key = c1.attrib['type']
                self.urls[key] = c1.text

            # <icon>
            elif c1.tag == 'icon':
                key = c1.attrib.pop('type', 'unknown')
                c1.attrib['value'] = c1.text
                self.icons[key] = self.icons.get(key, []) + [c1.attrib]

            # <bundle>
            elif c1.tag == 'bundle':
                type = c1.attrib.pop('type', 'unknown')
                runtime = c1.attrib.pop('runtime', 'unknown')
                sdk = c1.attrib.pop('sdk', 'unknown')
                value = c1.text
                self.bundle = {
                    'type': type,
                    'runtime': runtime,
                    'sdk': sdk,
                    'value': value
                }


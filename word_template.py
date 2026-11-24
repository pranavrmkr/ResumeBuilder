"""Fill the supplied Word resume template and export it through Microsoft Word."""
import os
import re
from io import BytesIO
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from profiles import normalise_profile
from resume_themes import DEFAULT_RESUME_THEME, RESUME_THEMES

TEMPLATE_PATH = Path(__file__).with_name('Resume template1.docx')
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
V = 'urn:schemas-microsoft-com:vml'
XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'w': W, 'a': A, 'v': V}


def _register_namespaces(contents):
    for _, (prefix, uri) in ET.iterparse(BytesIO(contents), events=('start-ns',)):
        if prefix != 'xml':
            ET.register_namespace(prefix or '', uri)


def _text(node):
    return ''.join(item.text or '' for item in node.iter(f'{{{W}}}t'))


def _serialize_xml(root, original):
    """Retain prefixes used in Word compatibility attributes as well as tags."""
    namespaces = {}
    for event, item in ET.iterparse(BytesIO(original), events=('start-ns', 'start')):
        if event == 'start':
            break
        namespaces[item[0]] = item[1]
    serialized = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    declared = set(re.findall(rb'xmlns:([\w]+)=', serialized))
    for prefix, uri in namespaces.items():
        if prefix and prefix != 'xml' and prefix.encode() not in declared:
            root.set(f'xmlns:{prefix}', uri)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def _set_control(control, value):
    """Replace control text while retaining its paragraph and run formatting."""
    content = control.find(f'{{{W}}}sdtContent')
    if content is None:
        return
    properties = control.find(f'{{{W}}}sdtPr')
    if properties is not None:
        for tag in ('showingPlcHdr', 'placeholder', 'temporary'):
            element = properties.find(f'{{{W}}}{tag}')
            if element is not None:
                properties.remove(element)
    run = next(content.iter(f'{{{W}}}r'), None)
    if run is None:
        run = ET.SubElement(content, f'{{{W}}}r')
    run_properties = run.find(f'{{{W}}}rPr')
    for child in list(run):
        if child is not run_properties:
            run.remove(child)
    for child in list(content):
        if child is not run:
            content.remove(child)
    parts = str(value).splitlines() or ['']
    for index, part in enumerate(parts):
        if index:
            ET.SubElement(run, f'{{{W}}}br')
        text = ET.SubElement(run, f'{{{W}}}t')
        text.text = part
        if part[:1].isspace() or part[-1:].isspace():
            text.set(f'{{{XML}}}space', 'preserve')


def _multiline(items):
    return '\n'.join(str(item).strip() for item in items if str(item).strip())


def _date_range(entry):
    return ' – '.join(value for value in (entry.get('start_date', ''), entry.get('end_date', '')) if value)


def _resume_text(profile):
    personal = profile['personal_info']
    hidden = set(profile['settings']['hidden_sections'])
    skills = []
    groups = {}
    for skill in (profile['skills'].values() if 'skills' not in hidden else ()):
        if skill['name'].strip():
            item = skill['name'].strip()
            if skill['proficiency'].strip():
                item += f" ({skill['proficiency'].strip()})"
            groups.setdefault(skill['category'].strip() or 'Skills', []).append(item)
    skills = [f"{category}: {' · '.join(names)}" for category, names in groups.items()]

    experiences = [entry for entry in profile['experience'].values() if 'experience' not in hidden
                   if any(value.strip() for value in entry.values())]
    dates = [_date_range(entry) for entry in experiences[:3]]
    roles = []
    for entry in experiences[:3]:
        roles.append(' | '.join(value for value in
                     (entry['job_title'], entry['company'], entry['location']) if value))
    while len(dates) < 3:
        dates.append('')
        roles.append('')
    accomplishments = []
    for entry in experiences:
        role = entry.get('job_title') or entry.get('company') or 'Experience'
        lines = [line.strip().lstrip('-• ') for line in entry['achievements'].splitlines() if line.strip()]
        accomplishments.extend(f'{role}: {line}' for line in lines)
    accomplishments.extend(
        f"{_date_range(entry)} | {' | '.join(value for value in (entry['job_title'], entry['company'], entry['location']) if value)}"
        for entry in experiences[3:]
    )

    education = [entry for entry in profile['education'].values() if 'education' not in hidden
                 if any(value.strip() for value in entry.values())]
    schools = []
    degrees = []
    for entry in education:
        schools.append(entry['institution'])
        degree = ' '.join(value for value in (entry['degree'], entry['field_of_study']) if value)
        dates_text = _date_range(entry)
        degrees.append(' · '.join(value for value in (degree, dates_text, entry['details']) if value))

    projects = []
    for entry in (profile['projects'].values() if 'projects' not in hidden else ()):
        if not any(value.strip() for value in entry.values()):
            continue
        title = entry['title'].strip() or 'Project'
        details = [title]
        if entry['technologies'].strip():
            details.append('Technologies: ' + entry['technologies'].strip())
        if entry['description'].strip():
            details.append(entry['description'].strip())
        if entry['contributions'].strip():
            details.extend(line.strip().lstrip('-• ') for line in entry['contributions'].splitlines() if line.strip())
        if entry['url'].strip():
            details.append(entry['url'].strip())
        projects.append(' | '.join(details))

    other = []
    for section in ('certifications', 'achievements'):
        for entry in (profile[section].values() if section not in hidden else ()):
            if any(value.strip() for value in entry.values()):
                label = 'Certification' if section == 'certifications' else 'Achievement'
                other.append(label + ': ' + ' | '.join(value.strip() for value in entry.values() if value.strip()))
    additional = profile['additional']
    for field, label in ((('languages', 'Languages'), ('professional_links', 'Links'),
                          ('portfolio', 'Portfolio'), ('github', 'GitHub'),
                          ('linkedin', 'LinkedIn'), ('extracurricular', 'Activities'))
                         if 'additional' not in hidden else ()):
        value = additional.get(field, '').strip()
        if value:
            other.append(f'{label}: {value}')

    contact_location = personal.get('location', '').strip()
    contact_site = personal.get('website', '').strip()
    if not contact_site and 'additional' not in hidden:
        contact_site = additional.get('portfolio', '').strip() or additional.get('linkedin', '').strip()
    summary = _multiline((personal.get('headline', ''), personal.get('summary', ''))) if 'summary' not in hidden else ''
    controls = {
        0: 'PROFILE' if summary else '',
        1: summary,
        2: 'SKILLS' if skills else '',
        3: _multiline(skills),
        4: 'LOCATION' if contact_location else '',
        5: contact_location,
        6: 'PHONE' if personal.get('phone', '').strip() else '',
        7: personal.get('phone', '').strip(),
        8: 'EMAIL' if personal.get('email', '').strip() else '',
        9: personal.get('email', '').strip(),
        10: 'WEBSITE' if contact_site else '',
        11: contact_site,
        12: 'EXPERIENCE' if experiences else '',
        13: dates[0], 14: roles[0],
        15: dates[1], 16: roles[1],
        17: dates[2], 18: roles[2],
        19: _multiline(accomplishments),
        20: 'EDUCATION' if education else '',
        21: _multiline(schools),
        22: _multiline(degrees),
        23: 'PROJECTS' if projects else '',
        24: _multiline(projects),
        25: 'ADDITIONAL' if other else '',
        26: _multiline(other),
    }
    return personal.get('full_name', '').strip(), controls


def _replace_colors(root, theme, *, recolor_panel=False):
    for node in root.iter():
        local = node.tag.rsplit('}', 1)[-1]
        if (local in ('color', 'fill', 'fillcolor') or 'fillcolor' in node.attrib
                or 'color' in node.attrib or f'{{{W}}}fill' in node.attrib):
            old = (node.get(f'{{{W}}}val') or node.get(f'{{{W}}}fill')
                   or node.get('color') or node.get('fillcolor'))
            if old and old.upper().lstrip('#') == '000000':
                if f'{{{W}}}val' in node.attrib:
                    node.set(f'{{{W}}}val', theme['text'])
                elif f'{{{W}}}fill' in node.attrib:
                    node.set(f'{{{W}}}fill', theme['text'])
                elif 'color' in node.attrib:
                    node.set('color', '#' + theme['text'])
                elif 'fillcolor' in node.attrib:
                    node.set('fillcolor', '#' + theme['text'])
            elif old and old.upper().lstrip('#') == '4A9A82':
                is_panel = local in ('shape', 'fill')
                replacement = theme['surface'] if is_panel else theme['accent']
                if f'{{{W}}}val' in node.attrib:
                    node.set(f'{{{W}}}val', replacement)
                elif f'{{{W}}}fill' in node.attrib:
                    node.set(f'{{{W}}}fill', replacement)
                elif 'color' in node.attrib:
                    node.set('color', '#' + replacement)
                elif 'fillcolor' in node.attrib:
                    node.set('fillcolor', '#' + replacement)
        # The template's decorative panel is the only DrawingML filled shape.
        if recolor_panel and node.tag == f'{{{A}}}solidFill':
            color = next((child for child in list(node)
                          if child.tag in (f'{{{A}}}schemeClr', f'{{{A}}}srgbClr')), None)
            if color is not None:
                color.tag = f'{{{A}}}srgbClr'
                color.attrib.clear()
                color.set('val', theme['surface'])


def make_filled_docx(profile, theme_name=DEFAULT_RESUME_THEME, output_path=None):
    """Create a temporary resume DOCX by filling the template's existing controls."""
    profile = normalise_profile(profile)
    theme = RESUME_THEMES.get(theme_name, RESUME_THEMES[DEFAULT_RESUME_THEME])
    if not TEMPLATE_PATH.is_file() or TEMPLATE_PATH.stat().st_size == 0:
        raise ValueError('The Word resume template is missing. Keep Resume template1.docx beside app.py.')
    name, control_values = _resume_text(profile)
    if not name:
        raise ValueError('Enter your full name before generating a resume.')

    temporary = output_path is None
    if temporary:
        handle = tempfile.NamedTemporaryFile(prefix='resume-', suffix='.docx', delete=False)
        output_path = Path(handle.name)
        handle.close()
    output_path = Path(output_path)
    try:
        with ZipFile(TEMPLATE_PATH, 'r') as source, ZipFile(output_path, 'w', ZIP_DEFLATED) as target:
            for item in source.infolist():
                contents = source.read(item.filename)
                if item.filename == 'word/document.xml':
                    _register_namespaces(contents)
                    root = ET.fromstring(contents)
                    controls = root.findall('.//{%s}sdt' % W)
                    if len(controls) != 27:
                        raise ValueError('This Word template has changed. Restore the supplied template before exporting.')
                    for index, control in enumerate(controls):
                        _set_control(control, control_values[index])
                    for text_node in root.iter(f'{{{W}}}t'):
                        if text_node.text == 'Pragdeesh Kumar P':
                            text_node.text = name
                    _replace_colors(root, theme, recolor_panel=True)
                    contents = _serialize_xml(root, contents)
                elif item.filename in ('word/styles.xml', 'word/theme/theme1.xml', 'word/numbering.xml'):
                    _register_namespaces(contents)
                    root = ET.fromstring(contents)
                    _replace_colors(root, theme)
                    if item.filename == 'word/theme/theme1.xml':
                        for node in root.iter():
                            if node.tag.endswith('}accent3'):
                                srgb = node.find(f'{{{A}}}srgbClr')
                                if srgb is not None:
                                    srgb.set('val', theme['accent'])
                    contents = _serialize_xml(root, contents)
                target.writestr(item, contents)
        return output_path
    except Exception:
        if temporary:
            output_path.unlink(missing_ok=True)
        raise


def export_pdf(profile, theme_name=DEFAULT_RESUME_THEME):
    """Render a filled template to PDF using the locally installed Microsoft Word."""
    if os.name != 'nt':
        raise ValueError('Word-template PDF export needs Microsoft Word on Windows. Use the built-in PDF template on this system.')
    try:
        import pythoncom
        from win32com.client import DispatchEx
    except ImportError:
        raise ValueError('Install the Windows PDF export dependency with: python -m pip install -r requirements.txt') from None
    with tempfile.TemporaryDirectory(prefix='resume-export-') as directory:
        source = Path(directory) / 'resume.docx'
        output = Path(directory) / 'resume.pdf'
        make_filled_docx(profile, theme_name, source)
        word = document = None
        try:
            pythoncom.CoInitialize()
            word = DispatchEx('Word.Application')
            word.Visible = False
            word.DisplayAlerts = 0
            document = word.Documents.Open(str(source.resolve()), ReadOnly=True, AddToRecentFiles=False)
            document.ExportAsFixedFormat(str(output.resolve()), 17)
            document.Close(False)
            document = None
            word.Quit()
            word = None
            return output.read_bytes()
        except Exception:
            raise ValueError('Microsoft Word could not render this resume. Check that Word is installed and the template opens normally.') from None
        finally:
            if document is not None:
                try:
                    document.Close(False)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

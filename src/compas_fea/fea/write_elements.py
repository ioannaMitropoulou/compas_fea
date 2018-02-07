
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from math import pi


__author__    = ['Andrew Liew <liew@arch.ethz.ch>']
__copyright__ = 'Copyright 2018, BLOCK Research Group - ETH Zurich'
__license__   = 'MIT License'
__email__     = 'liew@arch.ethz.ch'


__all__ = [
    'write_input_elements',
]


comments = {
    'abaqus':   '**',
    'opensees': '#',
    'sofistik': '$',
    'ansys':    '!',
}

footers = {
    'abaqus':   '',
    'opensees': '',
    'sofistik': 'END\n$\n$\n',
    'ansys':    '',
}

sdata = {
    'AngleSection':       {'name': 'L',           'geometry': ['b', 'h', 't', 't']},
    'BoxSection':         {'name': 'BOX',         'geometry': ['b', 'h', 'tw', 'tf', 'tw', 'tf']},
    'CircularSection':    {'name': 'CIRC',        'geometry': ['r']},
    'ISection':           {'name': 'I',           'geometry': ['c', 'h', 'b', 'b', 'tf', 'tf', 'tw']},
    'PipeSection':        {'name': 'PIPE',        'geometry': ['r', 't']},
    'RectangularSection': {'name': 'RECTANGULAR', 'geometry': ['b', 'h']},
    'TrapezoidalSection': {'name': 'TRAPEZOID',   'geometry': ['b1', 'h', 'b2', 'c']},
    'GeneralSection':     {'name': 'GENERAL',     'geometry': ['A', 'I11', 'I12', 'I22', 'J', 'g0', 'gw']},
    'ShellSection':       {'name': None,          'geometry': ['t']},
    'SolidSection':       {'name': None,          'geometry': None},
    'TrussSection':       {'name': None,          'geometry': ['A']}}


def write_input_elements(f, software, sections, properties, elements, structure, materials):

    """ Writes the element and section information to the input file.

    Parameters
    ----------
    f : obj
        The open file object for the .tcl file.
    software : str
        Analysis software or library to use, 'abaqus', 'opensees', 'sofistik' or 'ansys'.
    sections : dic
        Section objects from structure.sections.
    properties : dic
        ElementProperties objects from structure.element_properties.
    elements : dic
        Element objects from structure.elements.
    structure : obj
        The Structure object.
    materials : dic
        Material objects from structure.materials.

    Returns
    -------
    None

    """

    c = comments[software]

    shells = ['ShellSection']
    solids = ['SolidSection']
    trusses = ['TrussSection']

    f.write('{0} -----------------------------------------------------------------------------\n'.format(c))
    f.write('{0} -------------------------------------------------------------------- Elements\n'.format(c))
    f.write('{0}\n'.format(c))

    for key, property in properties.items():

        section = sections[property.section]
        section_index = section.index + 1
        material = materials[property.material]
        reinforcement = property.reinforcement
        if reinforcement:
            rebar_index = materials[reinforcement.values()[0]['material']].index + 1
        material_index = material.index + 1
        material_name = material.name
        geometry = section.geometry
        stype = section.__name__

        if property.elements:
            elset_name = 'elset_{0}'.format(key)
            structure.add_set(name=elset_name, type='element', selection=property.elements)
            elsets = [elset_name]
        else:
            elsets = property.elsets
            if isinstance(elsets, str):
                elsets = [elsets]
        sets = structure.sets

        f.write('{0} Property: {1}\n'.format(c, key))
        f.write('{0} ----------'.format(c) + '-' * (len(key)) + '\n')
        f.write('{0}\n'.format(c))

        for elset in elsets:

            if isinstance(elset, str) and (elset[:8] == 'element_'):
                selection = [int(elset[8:])]
            else:
                selection = sets[elset]['selection']
                set_index = sets[elset]['index'] + 1

            # Beam sections

            if stype not in shells + solids + trusses:

                if software == 'sofistik':
                    f.write('GRP {0} BASE {0}0000\n'.format(set_index))
                    f.write('$\n')

                for select in selection:

                    element = elements[select]
                    sp, ep = element.nodes
                    n = select + 1
                    i = sp + 1
                    j = ep + 1

                    if software == 'abaqus':

                        f.write('*ELEMENT, TYPE=B31, ELSET=element_{0}\n'.format(select))
                        f.write('{0}, {1},{2}\n'.format(n, i, j))

                        if stype == 'GeneralSection':
                            f.write('*BEAM GENERAL SECTION')
                        else:
                            f.write('*BEAM SECTION')

                        sname = sdata[stype]['name']
                        e1 = 'element_{0}'.format(select)
                        f.write(', SECTION={0}, ELSET={1}, MATERIAL={2}\n'.format(sname, e1, material_name))
                        f.write(', '.join([str(geometry[entry]) for entry in sdata[stype]['geometry']]) + '\n')

                        ex = element.axes.get('ex', None)
                        if ex:
                            f.write(', '.join([str(v) for v in ex]) + '\n')

                        f.write('**\n')

                    elif software == 'opensees':

                        E = material.E['E']
                        G = material.G['G']
                        A = geometry['A']
                        J = geometry['J']
                        Ixx = geometry['Ixx']
                        Iyy = geometry['Iyy']
                        # Avy = geometry['Avy']
                        # Avx = geometry['Avx']

                        ex = ' '.join([str(k) for k in element.axes['ex']])
                        et = 'element elasticBeamColumn'
                        f.write('geomTransf Corotational {0} {1}\n'.format(select + 1, ex))
                        f.write('{} {} {} {} {} {} {} {} {} {} {}\n'.format(et, n, i, j, A, E, G, J, Ixx, Iyy, n))
                        f.write('#\n')
                        # f.write('geomTransf PDelta {0} {1}\n'.format(n, ex))
                        # f.write('element ElasticTimoshenkoBeam {} {} {} {} {} {} {} {} {} {} {} {}\n'.format(n, i, j, E, G, A, J, Ixx, Iyy, Avy, Avx, n))

                    elif software == 'sofistik':

                        f.write('BEAM NO NA NE NCS\n')
                        f.write('{0} {1} {2} {3}\n'.format(n, i, j, section_index))
                        f.write('$\n')

            # Truss sections

            elif stype in trusses:

                if (software == 'opensees') and (material.__name__ == 'ElasticIsotropic'):

                    E = material.E['E']
                    f.write('uniaxialMaterial Elastic {0} {1}\n'.format(material_index, E))
                    f.write('#\n')

                for select in selection:

                    element = elements[select]
                    sp, ep = element.nodes
                    n = select + 1
                    i = sp + 1
                    j = ep + 1
                    A = geometry['A']

                    if software == 'abaqus':

                        if software == 'abaqus':

                            f.write('*ELEMENT, TYPE=T3D2, ELSET=element_{0}\n'.format(select))
                            f.write('{0}, {1},{2}\n'.format(n, i, j))
                            f.write('*SOLID SECTION, ELSET=element_{0}, MATERIAL={1}\n'.format(select, material_name))
                            f.write('{0}\n'.format(A))
                            f.write('**\n')

                    elif software == 'sofistik':

                        f.write('TRUS NO NA NE NCS\n')
                        f.write('{0} {1} {2} {3}\n'.format(n, i, j, section_index))
                        f.write('$\n')

                    elif software == 'opensees':

                        f.write('element corotTruss {0} {1} {2} {3} {4}\n'.format(n, i, j, A, material_index))
                        f.write('#\n')

            # Shell sections

            elif stype in shells:

                if software == 'sofistik':  # co-ordinate this with abaqus nsets
                    f.write('GRP {0} BASE {0}0000\n'.format(set_index))
                    f.write('$\n')

                for select in selection:

                    element = elements[select]
                    nodes = element.nodes
                    n = select + 1
                    t = geometry['t']

                    if software == 'abaqus':

                        if len(nodes) == 3:
                            etype = 'S3'
                        elif len(nodes) == 4:
                            etype = 'S4'

                        f.write('*ELEMENT, TYPE={0}, ELSET=element_{1}\n'.format(etype, select))
                        f.write('{0}, {1}\n'.format(n, ','.join([str(i + 1) for i in nodes])))

                        e1 = 'element_{0}'.format(select)
                        ex = element.axes.get('ex', None)
                        ey = element.axes.get('ey', None)
                        pre = '*SHELL SECTION, ELSET='

                        if ex and ey:
                            ori = 'ORI_element_{0}'.format(select)
                            f.write('*ORIENTATION, NAME={0}\n'.format(ori))
                            f.write(', '.join([str(j) for j in ex]) + ', ')
                            f.write(', '.join([str(j) for j in ey]) + '\n')
                            f.write('**\n')
                            f.write('{0}{1}, MATERIAL={2}, ORIENTATION={3}\n'.format(pre, e1, material_name, ori))
                        else:
                            f.write('{0}{1}, MATERIAL={2}\n'.format(pre, e1, material_name))

                        f.write(str(t) + '\n')

                        if reinforcement:
                            f.write('*REBAR LAYER\n')
                            for name, rebar in reinforcement.items():  # this can be moved outside the select loop
                                pos = rebar['pos']
                                spacing = rebar['spacing']
                                rmat = rebar['material']
                                angle = rebar['angle']
                                dia = rebar['dia']
                                A = 0.25 * pi * dia**2
                                if dia:
                                    f.write('{0}, {1}, {2}, {3}, {4}, {5}\n'.format(name, A, spacing, pos, rmat, angle))

                        f.write('**\n')

                    elif software == 'opensees':

                        E = material.E['E']
                        v = material.v['v']
                        p = material.p
                        ns = ' '.join([str(i + 1) for i in nodes])

                        if len(nodes) == 4:
                            f.write('section ElasticMembranePlateSection {0} {1} {2} {3} {4}\n'.format(n, E, v, t, p))
                            f.write('element ShellNLDKGQ {0} {1} {0}\n'.format(n, ns))
                            f.write('#\n')

                    elif software == 'sofistik':

                        data = [n] + [i + 1 for i in nodes] + [material_index] + [t] * len(nodes)
                        if reinforcement:
                            data.append(rebar_index)

                        if len(nodes) == 3:
                            pass
                        if len(nodes) == 4:
                            f.write('QUAD NO N1 N2 N3 N4 MNO T1 T2 T3 T4')
                            if reinforcement:
                                f.write(' MRF')
                            f.write('\n')
                        f.write('{0}\n'.format(' '.join([str(i) for i in data])))
                        f.write('$\n')

            # Solid sections

            elif stype in solids:

                if software == 'sofistik':
                    f.write('GRP {0} BASE {0}0000\n'.format(set_index))
                    f.write('$\n')

                for select in selection:

                    n = select + 1
                    element = elements[select]
                    nodes = element.nodes

                    if software == 'sofistik':

                        ns = ' '.join([str(i + 1) for i in nodes])

                        if len(nodes) == 8:
                            f.write('BRIC NO N1 N2 N3 N4 N5 N6 N7 N8 MNO\n')
                            f.write('{0} {1} {2}\n'.format(n, ns, material_index))

                        f.write('$\n')

                    elif software == 'opensees':

                        pass

                    elif software == 'ansys':

                        pass

                    elif software == 'abaqus':

                        if len(nodes) == 4:
                            etype = 'C3D4'
                        elif len(nodes) == 8:
                            etype = 'C3D8'

                        f.write('*ELEMENT, TYPE={0}, ELSET=element_{1}\n'.format(etype, select))
                        f.write('{0}, {1}\n'.format(n, ','.join([str(i + 1) for i in nodes])))
                        f.write('*SOLID SECTION, ELSET=element_{0}, MATERIAL={1}\n'.format(select, material_name))
                        f.write('\n')
                        f.write('**\n')

    f.write('{0}\n'.format(c))

    if footers[software]:
        f.write('{0}'.format(footers[software]))

    if software == 'sofistik':

        f.write('$\n')
        f.write('+PROG BEMESS\n')
        f.write('$\n')
        f.write('CTRL WARN 7\n')  # Upper cover (<10mm or >0.70d)
        f.write('CTRL WARN 9\n')  # Bottom cover (<10mm or >0.70d)
        f.write('CTRL WARN 471\n')  # Element thickness too thin and not allowed for design.
        f.write('$\n')

        for key, property in properties.items():

            reinforcement = property.reinforcement

            if reinforcement:

                f.write('$ Reinforcement: {0}\n'.format(key))
                f.write('$ ---------------' + '-' * (len(key)) + '\n')
                f.write('$\n')

                t = sections[property.section].geometry['t']
                posu, posl = [], []
                du, dl = [], []
                Au, Al = [], []

                for name, rebar in reinforcement.items():
                    pos = rebar['pos']
                    dia = rebar['dia']
                    spacing = rebar['spacing']
                    Ac = 0.25 * pi * (dia * 100)**2
                    Apm = Ac / spacing
                    if pos > 0:
                        posu.append(pos)
                        du.append(dia)
                        Au.append(Apm)
                    elif pos < 0:
                        posl.append(pos)
                        dl.append(dia)
                        Al.append(Apm)

                geom = 'GEOM -'
                data = ''

                if len(posu) == 1:
                    geom += ' HA {0}[mm]'.format((0.5 * t - posu[0]) * 1000)
                    data += ' DU {0}[mm] ASU {1}[cm2/m] BSU {2}[cm2/m]'.format(du[0] * 1000, Au[0], Au[0])

                elif len(posu) == 2:
                    if posu[0] > posu[1]:
                        no1 = 0
                        no2 = 1
                    else:
                        no1 = 1
                        no2 = 0
                    DHA = abs(posu[0] - posu[1]) * 1000
                    geom += ' HA {0}[mm] DHA {1}[mm]'.format((0.5 * t - posu[no1]) * 1000, DHA)
                    data += ' DU {0}[mm] ASU {1}[cm2/m] BSU {2}[cm2/m]'.format(du[no1] * 1000, Au[no1], Au[no1])
                    data += ' DU2 {0}[mm] ASU2 {1}[cm2/m] BSU2 {2}[cm2/m]'.format(du[no2] * 1000, Au[no2], Au[no2])

                if len(posl) == 1:
                    geom += ' HB {0}[mm]'.format((0.5 * t + posl[0]) * 1000)
                    data += ' DL {0}[mm] ASL {1}[cm2/m] BSL {2}[cm2/m]'.format(dl[0] * 1000, Al[0], Al[0])

                elif len(posl) == 2:
                    if posl[0] < posl[1]:
                        no1 = 0
                        no2 = 1
                    else:
                        no1 = 1
                        no2 = 0
                    DHB = abs(posl[0] - posl[1]) * 1000
                    geom += ' HB {0}[mm] DHB {1}[mm]'.format((0.5 * t + posl[no1]) * 1000, DHB)
                    data += ' DL {0}[mm] ASL {1}[cm2/m] BSL {2}[cm2/m]'.format(dl[no1] * 1000, Al[no1], Al[no1])
                    data += ' DL2 {0}[mm] ASL2 {1}[cm2/m] BSL2 {2}[cm2/m]'.format(dl[no2] * 1000, Al[no2], Al[no2])

                f.write(geom + '\n')
                f.write('$\n')

                if isinstance(property.elsets, str):
                    elsets = [property.elsets]

                f.write('PARA NOG - WKU 0.1[mm] WKL 0.1[mm]\n')
                for elset in elsets:
                    set_index = structure.sets[elset]['index'] + 1
                    f.write('PARA NOG {0}{1}\n'.format(set_index, data))

                f.write('$\n')
                f.write('$\n')

        f.write('END\n')
        f.write('$\n')
        f.write('$\n')










# _properties(f, sections, properties, elements, structure):
#     """ Writes the section information to the Abaqus .inp file.

#     written_springs = []

#         if property.elements:
#             elset_name = 'elset_{0}'.format(key)
#             structure.add_set(name=elset_name, type='element', selection=property.elements)
#             f.write('**\n')
#             f.write('*ELSET, ELSET={0}\n'.format(elset_name))
#             selection = [i + 1 for i in property.elements]
#             cnt = 0
#             cm = 9
#             for j in selection:
#                 f.write(str(j))
#                 if (cnt < cm) and (j != selection[-1]):
#                     f.write(',')
#                     cnt += 1
#                 elif cnt >= cm:
#                     f.write('\n')
#                     cnt = 0
#                 else:
#                     f.write('\n')
#             elsets = [elset_name]
#         else:
#             elsets = property.elsets

#         sets = structure.sets

#         for elset in elsets:

#             # Springs

#             if stype == 'SpringSection':

#                 if explode:
#                     for select in selection:
#                         e1 = 'element_{0}'.format(select)
#                         behaviour = 'BEH_{0}'.format(section.name)
#                         f.write('*CONNECTOR SECTION, ELSET={0}, BEHAVIOR=BEH_{1}\n'.format(e1, section.name))
#                         f.write('AXIAL\n')
#                         f.write('ORI_{0}_{1}\n'.format(select, section.name))
#                         f.write('**\n')
#                         f.write('*ORIENTATION, NAME=ORI_{0}_{1}\n'.format(select, section.name))
#                         ey = elements[select].axes.get('ey', None)
#                         ez = elements[select].axes.get('ez', None)
#                         f.write(', '.join([str(j) for j in ez]) + ', ')
#                         f.write(', '.join([str(j) for j in ey]) + '\n')
#                         f.write('**\n')

#                         if behaviour not in written_springs:
#                             f.write('*CONNECTOR BEHAVIOR, NAME=BEH_{0}\n'.format(section.name))
#                             f.write('**\n')
#                             if section.stiffness:
#                                 f.write('*CONNECTOR ELASTICITY, COMPONENT=1\n')
#                                 f.write('{0}\n'.format(section.stiffness))
#                             else:
#                                 f.write('*CONNECTOR ELASTICITY, COMPONENT=1, NONLINEAR\n')
#                                 for i, j in zip(section.forces, section.displacements):
#                                     f.write('{0}, {1}\n'.format(i, j))
#                             written_springs.append(behaviour)
#                 else:

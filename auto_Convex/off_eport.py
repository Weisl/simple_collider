def off_export(mesh, fullpath):
    '''Export triangulated mesh to Object File Format'''
    with open(fullpath, 'wb') as off:
        off.write(b'OFF\n')
        off.write(str.encode('{} {} 0\n'.format(len(mesh.vertices), len(mesh.polygons))))
        for vert in mesh.vertices:
            off.write(str.encode('{:g} {:g} {:g}\n'.format(*vert.co)))

        # Faces are not needed ?!
        # for face in mesh.polygons:
        #     off.write(str.encode('3 {} {} {}\n'.format(*face.vertices)))

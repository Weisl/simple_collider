import blf
import bpy
import bmesh
import time
import numpy

from ..pyshics_materials.material_functions import remove_materials, set_material, make_physics_material

collider_types = ['SIMPLE_COMPLEX','SIMPLE', 'COMPLEX']

def draw_modal_item(self, font_id,i,vertical_px_offset, left_margin, label, value = None, type = 'default', key = '', highlight = False):
    """Draw label in the 3D Viewport"""

    # get colors from preferences
    col_default = self.prefs.modal_color_default
    color_title = self.prefs.modal_color_title
    color_ignore_input = [0.5, 0.5, 0.5, 0.5]

    #operator colors
    color_enum = self.prefs.modal_color_enum
    color_modal = self.prefs.modal_color_modal
    color_bool = self.prefs.modal_color_bool
    color_highlight = self.prefs.modal_color_highlight

    font_size = self.prefs.modal_font_size

    blf.size(font_id, 20, font_size)

    if type == 'key_title':
        if self.ignore_input or self.navigation:
            blf.color(font_id, color_highlight[0], color_highlight[1], color_highlight[2], color_highlight[3])
    elif self.ignore_input or self.navigation:
        blf.color(font_id, color_ignore_input[0], color_ignore_input[1], color_ignore_input[2], color_ignore_input[3])
    elif type == 'title':
        blf.color(font_id, color_title[0], color_title[1], color_title[2], color_title[3])
    else: #type == 'default'
        if highlight:
            blf.color(font_id, color_highlight[0], color_highlight[1], color_highlight[2], color_highlight[3])
        else:
            blf.color(font_id, col_default[0], col_default[1], col_default[2], col_default[3])

    blf.position(font_id, left_margin, i * vertical_px_offset, 0)
    blf.draw(font_id, label)

    if key:
        if self.ignore_input or self.navigation:
            blf.color(font_id, color_ignore_input[0], color_ignore_input[1], color_ignore_input[2], color_ignore_input[3])
        elif highlight:
            blf.color(font_id, color_highlight[0], color_highlight[1], color_highlight[2], color_highlight[3])
        elif type == 'bool':
            blf.color(font_id, color_bool[0], color_bool[1], color_bool[2], color_bool[3])
        elif type == 'enum':
            blf.color(font_id, color_enum[0], color_enum[1], color_enum[2], color_enum[3])
        elif type == 'modal':
            blf.color(font_id, color_modal[0], color_modal[1], color_modal[2], color_modal[3])
        else:  # type == 'default':
            blf.color(font_id, col_default[0], col_default[1], col_default[2], col_default[3])

        blf.position(font_id, left_margin + 220/72 * font_size, i * vertical_px_offset, 0)
        blf.draw(font_id, key)

    if value:

        if self.ignore_input or self.navigation:
            blf.color(font_id, color_ignore_input[0], color_ignore_input[1], color_ignore_input[2], color_ignore_input[3])
        elif highlight:
            blf.color(font_id, color_highlight[0], color_highlight[1], color_highlight[2], color_highlight[3])
        else:  # type == 'default':
            blf.color(font_id, col_default[0], col_default[1], col_default[2], col_default[3])

        blf.position(font_id, left_margin + 290/72 * font_size, i * vertical_px_offset, 0)
        blf.draw(font_id, value)

    i += 1
    return i

def create_name_number(name, nr):
    nr = str('_{num:{fill}{width}}'.format(num=(nr), fill='0', width=3))
    return name + nr

def draw_viewport_overlay(self, context):
    """Draw 3D viewport overlay for the modal operator"""
    scene = context.scene

    font_id = 0  # XXX, need to find out how best to get this.
    font_size = self.prefs.modal_font_size
    vertical_px_offset = 30/72 * font_size
    left_margin = bpy.context.area.width / 2 - 190/72 * font_size
    i = 1

    if self.use_space:
        label = "Global/Local"
        value = "GLOBAL" if scene.my_space == 'GLOBAL' else "LOCAL"
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(G/L)', type='enum')

    label = "Display Wireframe "
    value = str(scene.wireframe_mode)
    i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(W)', type='enum')

    label = "Hide After Creation "
    value = str(scene.my_hide)
    i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(H)', type='bool')

    label = "Opacity"
    value = self.current_settings_dic['alpha']
    value = '{initial_value:.3f}'.format(initial_value=value)
    i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(A)', type='modal', highlight = self.opacity_active )

    label = 'Persistent Settings'
    i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, type='title')

    label = "Collider Complexity"
    value = str(self.collision_type[self.collision_type_idx])
    i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(T)', type='enum')

    if context.space_data.shading.type == 'SOLID':
        label = "Preview View "
        value = self.shading_modes[self.shading_idx]
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(V)', type='enum')

    if self.use_type_change:
        label= "Collider Shape"
        value = self.get_shape_name(self.collider_shapes[self.collider_shapes_idx])
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(C)', type='enum')

    if self.use_cylinder_axis:
        label = "Cylinder Axis"
        value = str(self.cylinder_axis)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(X/Y/Z)', type='enum')

    if self.use_modifier_stack:
        label = "Use Modifiers "
        value = str(self.my_use_modifier_stack)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(P)', type='bool')

    label = "Shrink/Inflate"
    value = self.current_settings_dic['discplace_offset']
    value = '{initial_value:.3f}'.format(initial_value=value)
    i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value=value, key='(S)', type='modal', highlight=self.displace_active)

    if self.use_sphere_segments:
        label = "Sphere Segments "
        value = str(self.current_settings_dic['sphere_segments'])
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value = value, key='(R)', type='modal', highlight=self.sphere_segments_active)

    if self.use_decimation:
        label = "Decimate Ratio"
        value = self.current_settings_dic['decimate']
        value = '{initial_value:.3f}'.format(initial_value=value)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value=value,  key='(D)', type='modal', highlight=self.decimate_active)

    if self.use_vertex_count:
        label = "Segments"
        value = str(self.current_settings_dic['cylinder_segments'])
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, value=value, key='(E)', type='modal', highlight=self.vertex_count_active)


    label = 'Operator Settings'
    i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, type='title')

    if self.navigation:
        label = 'VIEWPORT NAVIGATION'
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, type='key_title', highlight=True)

    elif self.ignore_input:
        label = 'IGNORE INPUT (ALT)'
        i = draw_modal_item(self, font_id, i, vertical_px_offset, left_margin, label, type='key_title', highlight=True)


class OBJECT_OT_add_bounding_object():
    """Abstract parent class for modal operators contain common methods and properties for all add bounding object operators"""
    bl_options = {'REGISTER', 'UNDO'}
    bm = []

    @classmethod
    def bmesh(cls, bm):
        #append bmesh to class for it not to be deleted
        cls.bm.append(bm)

    def collision_dictionary(self, alpha, offset, decimate, sphere_segments, cylinder_segments):
        dict = {}
        dict['alpha'] = alpha
        dict['discplace_offset'] = offset
        dict['decimate'] = decimate
        dict['sphere_segments'] = sphere_segments
        dict['cylinder_segments'] = cylinder_segments

        return dict

    def get_shape_name(self, identifier):
        if identifier == 'boxColSuffix':
            return 'BOX'
        elif identifier == 'sphereColSuffix':
            return 'SPHERE'
        elif identifier == 'convexColSuffix':
            return 'CONVEX'
        else: # identifier == 'meshColSuffix':
            return 'MESH'

    def force_redraw(self):
        bpy.context.space_data.overlay.show_text = not bpy.context.space_data.overlay.show_text
        bpy.context.space_data.overlay.show_text = not bpy.context.space_data.overlay.show_text
        pass

    def set_collisions_wire_preview(self, mode):
        if mode in ['PREVIEW', 'ALWAYS']:
            for obj in self.new_colliders_list:
                obj.show_wire = True
        else:
            for obj in self.new_colliders_list:
                obj.show_wire = False


    def remove_objects(self, list):
        '''Remove previously created collisions'''
        if len(list) > 0:
            for ob in list:
                objs = bpy.data.objects
                objs.remove(ob, do_unlink=True)

    def custom_set_parent(self, context, parent, child):
        '''Custom set parent'''
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = parent
        parent.select_set(True)
        child.select_set(True)

        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)

    def generate_bounding_box(self, positionsX, positionsY, positionsZ):
        '''get the min and max coordinates for the bounding box'''
        verts = [
            (max(positionsX), max(positionsY), min(positionsZ)),
            (max(positionsX), min(positionsY), min(positionsZ)),
            (min(positionsX), min(positionsY), min(positionsZ)),
            (min(positionsX), max(positionsY), min(positionsZ)),
            (max(positionsX), max(positionsY), max(positionsZ)),
            (max(positionsX), min(positionsY), max(positionsZ)),
            (min(positionsX), min(positionsY), max(positionsZ)),
            (min(positionsX), max(positionsY), max(positionsZ)),
        ]
        return verts

    def get_delta_value(self, delta, event, sensibility=0.05, tweak_amount=10, round_precission=0):

        delta = delta * sensibility

        if event.ctrl:  # snap
            delta = round(delta, round_precission)
        if event.shift:  # tweak
            delta /= tweak_amount

        return delta

    def get_mesh_Edit(self, obj, use_modifiers=False):
        ''' Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no vertices to return '''
        me = obj.data
        me.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)

        new_mesh = bpy.data.meshes.new('')

        if use_modifiers:  # self.my_use_modifier_stack == True
            # Get mesh information with the modifiers applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)

        else:  # use_modifiers == False
            # Get a BMesh representation
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()

        vertices_select = [v for v in bm.verts if not v.select]
        bmesh.ops.delete(bm, geom=vertices_select)

        bm.verts.ensure_lookup_table()
        bm.to_mesh(new_mesh)

        if len(bm.faces) < 1:
            return None
        
        return new_mesh

    def get_vertices_Edit(self, obj, use_modifiers=False):
        ''' Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no vertices to return '''
        me = obj.data
        me.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)

        if use_modifiers:  # self.my_use_modifier_stack == True
            # Get mesh information with the modifiers applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            bm.verts.ensure_lookup_table()

        else:  # use_modifiers == False
            # Get a BMesh representation
            bm = bmesh.from_edit_mesh(me)

        used_vertices = [v for v in bm.verts if v.select]

        if len(used_vertices) == 0:
            return None

        #This is needed for the bmesh not bo be destroyed, even if the variable isn't used later.
        OBJECT_OT_add_bounding_object.bmesh(bm)
        return used_vertices

    def get_vertices_Object(self, obj, use_modifiers = False):
        ''' Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no vertices to return '''
        # bpy.ops.object.mode_set(mode='EDIT')
        me = obj.data
        me.update() # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)

        if use_modifiers:
            # Get mesh information with the modifiers applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            bm.verts.ensure_lookup_table()
            used_vertices = bm.verts

            # This is needed for the bmesh not bo be destroyed, even if the variable isn't used later.
            OBJECT_OT_add_bounding_object.bmesh(bm)

        else:
            # Get a BMesh representation
            used_vertices = me.vertices

        if len(used_vertices) == 0:
            return None

        return used_vertices


    def mesh_from_selection(self, obj, use_modifiers = False):
        mesh = obj.data.copy()
        mesh.update()  # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)

        bm = bmesh.new()

        if use_modifiers:
            # Get mesh information with the modifiers applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

        else:  # self.my_use_modifier_stack == False:
            bm.from_mesh(mesh)

        bm.to_mesh(mesh)
        bm.free()

        return mesh

    def get_point_positions(self, obj, space, used_vertives):
        """ returns vertex and face information for the bounding box based on the given coordinate space (e.g., world or local)"""

        # Modify the BMesh, can do anything here...
        positionsX = []
        positionsY = []
        positionsZ = []

        if space == 'GLOBAL':
            # get world space coordinates of the vertices
            for v in used_vertives:
                v_local = v
                v_global = obj.matrix_world @ v_local.co

                positionsX.append(v_global[0])
                positionsY.append(v_global[1])
                positionsZ.append(v_global[2])

        else: # space == 'LOCAL'
            for v in used_vertives:
                positionsX.append(v.co.x)
                positionsY.append(v.co.y)
                positionsZ.append(v.co.z)

        return positionsX, positionsY, positionsZ

    def primitive_postprocessing(self, context, bounding_object, base_object_collections):

        self.set_viewport_drawing(context, bounding_object)
        self.add_displacement_modifier(context, bounding_object)
        self.set_collections(bounding_object, base_object_collections)

        if self.prefs.use_col_collection:
            collection_name = self.prefs.col_collection_name
            self.add_to_collections(bounding_object, collection_name)

        if self.use_decimation:
            self.add_decimate_modifier(context, bounding_object)

        self.set_physics_material(context, bounding_object)

        bounding_object['isCollider'] = True
        bounding_object['collider_type'] = self.collision_type[self.collision_type_idx]

        scene = context.scene

        if scene.wireframe_mode in ['PREVIEW', 'ALWAYS']:
            bounding_object.show_wire = True
        else:
            bounding_object.show_wire = False

    def set_viewport_drawing(self, context, bounding_object):
        ''' Assign material to the bounding object and set the visibility settings of the created object.'''
        bounding_object.display_type = 'SOLID'
        self.set_object_color(bounding_object)

    def set_object_color(self, obj):
        if self.collision_type[self.collision_type_idx] == 'SIMPLE_COMPLEX':
            obj.color = self.prefs.my_color_simple_complex
        elif self.collision_type[self.collision_type_idx] == 'SIMPLE':
            obj.color = self.prefs.my_color_simple
        elif self.collision_type[self.collision_type_idx] == 'COMPLEX':
            obj.color = self.prefs.my_color_complex

    def set_object_type(self, obj):
        obj['collider_type'] = self.collision_type[self.collision_type_idx]

    def get_complexity_suffix(self):

        if self.collision_type[self.collision_type_idx] == 'SIMPLE_COMPLEX':
            suffix = self.prefs.colSimpleComplex
        elif self.collision_type[self.collision_type_idx] == 'SIMPLE':
            suffix = self.prefs.colSimple
        elif self.collision_type[self.collision_type_idx] == 'COMPLEX':
            suffix = self.prefs.colComplex

        return suffix

    def add_to_collections(self, obj, collection_name):
        if collection_name not in bpy.data.collections:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)

        col = bpy.data.collections[collection_name]

        try:
            col.objects.link(obj)
        except RuntimeError as err:
            print("RuntimeError: {0}".format(err))

    def set_collections(self, obj, collections):
        old_collection = obj.users_collection

        for col in collections:
            try:
                col.objects.link(obj)
            except RuntimeError:
                pass

        for col in old_collection:
            if col not in collections:
                col.objects.unlink(obj)

    def print_generation_time(self, shape):
        print(shape)
        print("Time elapsed: ", str(self.get_time_elapsed()))

    def unique_name(self, name):
        '''recursive function to find unique name'''
        new_name = create_name_number(name, self.name_count)

        while new_name in bpy.data.objects:
            self.name_count = self.name_count + 1
            new_name = create_name_number(name, self.name_count)

        self.name_count = self.name_count + 1
        return new_name

    def collider_name(self, basename = 'Basename'):
        separator = self.prefs.separator

        if self.prefs.replace_name:
            name = self.prefs.basename
        else:
            name = basename

        if self.prefs.IgnoreShapeForComplex and self.collision_type[self.collision_type_idx] == 'COMPLEX':
            pre_suffix_componetns = [
                self.prefs.colPreSuffix,
                self.get_complexity_suffix(),
                self.prefs.optionalSuffix
            ]

        else:
            pre_suffix_componetns = [
                self.prefs.colPreSuffix,
                self.type_suffix,
                self.get_complexity_suffix(),
                self.prefs.optionalSuffix
            ]

        name_pre_suffix = ''

        if self.prefs.naming_position == 'SUFFIX':
            for comp in pre_suffix_componetns:
                if comp:
                    name_pre_suffix = name_pre_suffix + separator + comp
            new_name = name + name_pre_suffix

        else: #self.prefs.naming_position == 'PREFIX'
            for comp in pre_suffix_componetns:
                if comp:
                    name_pre_suffix = name_pre_suffix + comp + separator
            new_name = name_pre_suffix + name

        return self.unique_name(new_name)

    def update_names(self):
        for obj in self.new_colliders_list:
            obj.name = self.collider_name()

    def reset_to_initial_state(self, context):
        for obj in bpy.data.objects:
            obj.select_set(False)
        for obj in self.selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode=self.obj_mode)

        # infomessage = 'Generated collisions %d/%d' % (i, obj_amount)
        # self.report({'INFO'}, infomessage)

    #Modifiers
    def apply_all_modifiers(self,context, obj):
        context.view_layer.objects.active = obj
        for mod in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=mod.name)

    def remove_all_modifiers(self, context, obj):
        context.view_layer.objects.active = obj
        if obj:
            for mod in obj.modifiers:
                obj.modifiers.remove(mod)

    def add_displacement_modifier(self, context, bounding_object):
        scene = context.scene

        # add displacement modifier and safe it to manipulate the strenght in the modal operator
        modifier = bounding_object.modifiers.new(name="Collision_displace", type='DISPLACE')
        modifier.strength = self.current_settings_dic['discplace_offset']

        self.displace_modifiers.append(modifier)

    def del_displace_modifier(self,context,bounding_object):
        if bounding_object.modifiers.get('Collision_displace'):
            mod = bounding_object.modifiers['Collision_displace']
            bounding_object.modifiers.remove(mod)

    def add_decimate_modifier(self, context, bounding_object):
        scene = context.scene

        # add decimation modifier and safe it to manipulate the strenght in the modal operator
        modifier = bounding_object.modifiers.new(name="Collision_decimate", type='DECIMATE')
        modifier.ratio = self.current_settings_dic['decimate']
        self.decimate_modifiers.append(modifier)

    def del_decimate_modifier(self,context,bounding_object):
        if bounding_object.modifiers.get('Collision_decimate'):
            mod = bounding_object.modifiers['Collision_decimate']
            bounding_object.modifiers.remove(mod)

    #Materials
    def set_physics_material(self, context, bounding_object):
        remove_materials(bounding_object)
        if self.physics_material_name:
            set_material(bounding_object, self.physics_material_name)
        else:
            # default_material = make_physics_material('COL_DEFAULT',(0.75, 0.25, 0.25, 0.5))
            default_material = make_physics_material('COL_DEFAULT',(1, 1, 1, 0.5))
            bpy.context.scene.CollisionMaterials = default_material
            set_material(bounding_object, default_material)

    def get_time_elapsed(self):
        t1 = time.time() - self.t0
        return t1

    def __init__(self):
        # has to be in --init
        self.is_mesh_to_collider = False
        self.use_decimation = False

        self.use_vertex_count = False
        self.vertex_count = 8
        self.use_modifier_stack = False

        self.use_space = False
        self.use_cylinder_axis = False
        self.use_global_local_switches = False
        self.use_sphere_segments = False
        self.type_suffix = ''
        self.use_type_change = False

        #UI/UX
        self.ignore_input = False


    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def invoke(self, context, event):
        global collider_types

        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

        # get collision suffix from preferences
        self.prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        scene = context.scene

        # Active object
        if context.object is None:
            context.view_layer.objects.active = context.selected_objects[0]
        context.object.select_set(True)

        # INITIAL STATE
        self.navigation = False
        self.selected_objects = context.selected_objects.copy()
        self.active_obj = context.view_layer.objects.active
        self.obj_mode = context.object.mode
        self.prev_decimate_time = time.time()

        # Mouse
        self.mouse_initial_x = event.mouse_x

        #Modal Settings
        self.my_use_modifier_stack = False

        # Modal MODIFIERS
        #Displace
        self.displace_active = False
        self.displace_modifiers = []

        # Decimate
        self.decimate_active = False
        self.decimate_modifiers = []

        #Opacity
        self.opacity_active = False
        self.opacity_ref = 0.5

        self.cylinder_axis = 'Z'

        self.vertex_count_active = False

        self.sphere_segments_active = False
        segments = 16

        self.color_type = context.space_data.shading.color_type
        self.shading_idx = 0
        self.shading_modes = ['OBJECT','MATERIAL','SINGLE']
        self.wireframe_idx = 1
        # self.wireframe_mode = ['OFF', 'PREVIEW', 'ALWAYS']
        self.collision_type_idx = 0
        self.collision_type = collider_types

        # Physics Materials
        self.physics_material_name = scene.CollisionMaterials
        self.new_colliders_list = []

        self.name_count = 0

        # Set up scene
        if context.space_data.shading.type == 'SOLID':
            context.space_data.shading.color_type = self.shading_modes[self.shading_idx]

        dict = self.collision_dictionary(0.5, 0, 1.0, segments, self.vertex_count)
        self.current_settings_dic = dict.copy()
        self.ref_settings_dic = dict.copy()

        # the arguments we pass the the callback
        args = (self, context)
        # Add the region OpenGL drawing callback
        # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_viewport_overlay, args, 'WINDOW', 'POST_PIXEL')
        # add modal handler
        context.window_manager.modal_handler_add(self)
        self.execute(context)

    def modal(self, context, event):
        scene = context.scene
        self.navigation = False

        # Ignore if Alt is pressed
        if event.alt:
            self.ignore_input = True
            self.force_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            # allow navigation
            self.navigation = True

            self.opacity_active = False
            self.displace_active = False
            self.decimate_active = False
            self.vertex_count_active = False
            self.sphere_segments_active = False
            
            return {'PASS_THROUGH'}

        # User Input
        # aboard operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:

            if not self.is_mesh_to_collider:
                # Remove previously created collisions
                if self.new_colliders_list != None:
                    for obj in self.new_colliders_list:
                        objs = bpy.data.objects
                        objs.remove(obj, do_unlink=True)

            # Reset Convert Mesh to Collider
            else:
                if self.new_colliders_list != None:
                    for obj, data in zip(self.new_colliders_list, self.original_obj_data):
                        if self.prefs.col_collection_name in bpy.data.collections:
                            col = bpy.data.collections[self.prefs.col_collection_name]
                            if obj.name in col.objects:
                                col.objects.unlink(obj)

                        obj.color = data['color']
                        obj.show_wire = data['show_wire']
                        obj.name = data['name']

                        remove_materials(obj)
                        for mat in data['material_slots']:
                            set_material(obj,bpy.data.materials[mat])

                        self.del_displace_modifier(context, obj)
                        self.del_decimate_modifier(context, obj)

            context.space_data.shading.color_type = self.color_type


            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass

            return {'CANCELLED'}

        # apply operator
        elif event.type in {'LEFTMOUSE', 'NUMPAD_ENTER', 'RET'}:
            # self.execute(context)
            if bpy.context.space_data.shading.color_type:
                context.space_data.shading.color_type = self.color_type

            for obj in self.new_colliders_list:
                # remove modifiers if they have the default value
                if self.current_settings_dic['discplace_offset'] == 0.0:
                    self.del_displace_modifier(context,obj)
                if self.current_settings_dic['decimate'] == 1.0:
                    self.del_decimate_modifier(context,obj)

                # set the display settings for the collider objects
                obj.display_type = scene.my_collision_shading_view
                if scene.my_hide:
                    obj.hide_viewport = scene.my_hide

                if scene.wireframe_mode == 'ALWAYS':
                    obj.show_wire = True
                else:
                    obj.show_wire = False

            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass

            bpy.ops.object.mode_set(mode='OBJECT')

            return {'FINISHED'}

        # Set ref values when switching mode to avoid jumping of field of view.
        elif event.type in ['LEFT_SHIFT','LEFT_CTRL'] and event.value in ['PRESS', 'RELEASE']:
            self.ref_settings_dic = self.current_settings_dic.copy()

            # update ref mouse position to current
            self.mouse_initial_x = event.mouse_x
            #Alt is not pressed anymore after release
            self.ignore_input = False

            return {'RUNNING_MODAL'}

        # Ignore Mouse Movement. The Operator will behave as starting it newly
        elif event.type == 'LEFT_ALT' and event.value == 'RELEASE':
            self.ref_settings_dic = self.current_settings_dic.copy()

            # update ref mouse position to current
            self.mouse_initial_x = event.mouse_x

            #Alt is not pressed anymore after release
            self.ignore_input = False
            self.force_redraw()
            return {'RUNNING_MODAL'}

        # hide after creation
        elif event.type == 'H' and event.value == 'RELEASE':
            scene.my_hide = not scene.my_hide
            #Another function needs to be called for the modal UI to update :(
            self.set_collisions_wire_preview(scene.wireframe_mode)

        elif event.type == 'W' and event.value == 'RELEASE':
            self.wireframe_idx = (self.wireframe_idx + 1) % len(bpy.types.Scene.bl_rna.properties['wireframe_mode'].enum_items)
            scene.wireframe_mode = bpy.types.Scene.bl_rna.properties['wireframe_mode'].enum_items[self.wireframe_idx].identifier
            self.set_collisions_wire_preview(scene.wireframe_mode)

        elif event.type == 'S' and event.value == 'RELEASE':
            self.displace_active = not self.displace_active
            self.opacity_active = False
            self.decimate_active = False
            self.vertex_count_active = False
            self.sphere_segments_active = False
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'D' and event.value == 'RELEASE':
            self.decimate_active = not self.decimate_active
            self.opacity_active = False
            self.displace_active = False
            self.vertex_count_active = False
            self.sphere_segments_active = False
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'A' and event.value == 'RELEASE':
            self.opacity_active = not self.opacity_active
            self.displace_active = False
            self.decimate_active = False
            self.vertex_count_active = False
            self.sphere_segments_active = False
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'E' and event.value == 'RELEASE':
            self.vertex_count_active = not self.vertex_count_active
            self.displace_active = False
            self.decimate_active = False
            self.opacity_active = False
            self.sphere_segments_active = False
            self.mouse_initial_x = event.mouse_x

        elif event.type == 'V' and event.value == 'RELEASE':
            #toggle through display modes
            self.shading_idx = (self.shading_idx + 1) % len(self.shading_modes)
            context.space_data.shading.color_type = self.shading_modes[self.shading_idx]

        elif event.type == 'T' and event.value == 'RELEASE':
            #toggle through display modes
            self.collision_type_idx = (self.collision_type_idx + 1) % len(self.collision_type)
            for obj in self.new_colliders_list:
                self.set_object_color(obj)
                self.set_object_type(obj)
                self.update_names()

        elif event.type == 'MOUSEMOVE':
            # calculate mouse movement and offset camera
            delta = int(self.mouse_initial_x - event.mouse_x)

            # Ignore if Alt is pressed
            if event.alt:
                self.ignore_input = True
                return {'RUNNING_MODAL'}

            if self.displace_active:
                offset = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precission=1)
                strenght = self.ref_settings_dic['discplace_offset'] - offset

                for mod in self.displace_modifiers:
                    mod.strength = strenght
                    mod.show_on_cage = True
                    mod.show_in_editmode = True

                self.current_settings_dic['discplace_offset'] = strenght

            if self.decimate_active:
                delta = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precission=1)
                dec_amount = (self.ref_settings_dic['decimate'] + delta)
                dec_amount = numpy.clip(dec_amount, 0.01, 1.0)

                if self.current_settings_dic['decimate'] != dec_amount:
                    self.current_settings_dic['decimate'] = dec_amount

                    # I had to iterate over all object because it crashed when just iterating over the modifiers.
                    for obj in self.new_colliders_list:
                        for mod in obj.modifiers:
                            if mod in self.decimate_modifiers:
                                mod.ratio = dec_amount

            if self.opacity_active:
                delta = self.get_delta_value(delta, event, sensibility=0.002, tweak_amount=10, round_precission=1)
                color_alpha = self.ref_settings_dic['alpha'] - delta
                color_alpha = numpy.clip(color_alpha, 0.00, 1.0)

                for obj in self.new_colliders_list:
                    obj.color[3] = color_alpha

                self.prefs.my_color_simple_complex[3] = color_alpha
                self.current_settings_dic['alpha'] = color_alpha

            if self.vertex_count_active:
                delta = self.get_delta_value(delta, event, sensibility=0.02, tweak_amount=10)
                vertex_count = int(abs(self.ref_settings_dic['cylinder_segments'] - delta))

                # check if value changed to avoid regenerating collisions for the same value
                if vertex_count != int(round(self.vertex_count)):
                    self.vertex_count = vertex_count
                    self.current_settings_dic['cylinder_segments'] = vertex_count
                    self.execute(context)

            if self.sphere_segments_active:
                delta = self.get_delta_value(delta, event, sensibility=0.02, tweak_amount=10)
                segments = int(abs(self.ref_settings_dic['sphere_segments'] - delta))

                # check if value changed to avoid regenerating collisions for the same value
                if segments != int(round(self.current_settings_dic['sphere_segments'])):
                    self.current_settings_dic['sphere_segments'] = segments
                    self.execute(context)

        # passthrough specific events to blenders default behavior
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # get current time to calculate time elapsed
        self.t0 = time.time()
        # reset naming count:
        self.name_count = 0

        self.obj_mode = context.object.mode

        #Remove objects from previous generation
        self.remove_objects(self.new_colliders_list)
        self.new_colliders_list = []

        # reset previously stored displace modifiers when creating a new object
        self.displace_modifiers = []

        # Create the bounding geometry, depending on edit or object mode.
        self.old_objs = set(context.scene.objects)


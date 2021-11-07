import blf
import bpy
import bmesh

from ..pyshics_materials.material_functions import remove_materials, set_material, make_physics_material

collider_types = ['SIMPLE_COMPLEX','SIMPLE', 'COMPLEX']

def draw_modal_item(self, font_id,i,vertical_px_offset, text, color_type = 'operator'):
    if color_type == 'operator':
        blf.color(font_id, self.prefs.modal_font_color[0],self.prefs.modal_font_color[1], self.prefs.modal_font_color[2], self.prefs.modal_font_color[3])
    else:
        blf.color(font_id, self.prefs.modal_font_color_scene[0],self.prefs.modal_font_color_scene[1], self.prefs.modal_font_color_scene[2], self.prefs.modal_font_color_scene[3])

    blf.position(font_id, 30, i * vertical_px_offset, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, text)
    i += 1
    return i


def draw_viewport_overlay(self, context):

    scene = context.scene

    font_id = 0  # XXX, need to find out how best to get this.
    vertical_px_offset = 30
    i = 1


    if self.use_space:
        # draw some text
        global_orient = "ON" if scene.my_space == 'GLOBAL' else "OFF"
        text = "Global Orient (G): " + global_orient
        i = draw_modal_item(self, font_id, i, vertical_px_offset, text, color_type='scene')

        # draw some text
        local_orient = "ON" if scene.my_space == 'LOCAL' else "OFF"
        text= "Local Orient (L): " + local_orient
        i = draw_modal_item(self,font_id, i, vertical_px_offset, text, color_type='scene')

    text = "Shrink/Inflate (S): " + str(self.displace_my_offset)
    i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    text = "Opacity (A) : " + str(scene.my_color[3])
    i = draw_modal_item(self, font_id, i, vertical_px_offset, text,color_type='scene')

    text = "Preview View (V) : " + self.shading_modes[self.shading_idx]
    i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    text = "Collider Type (T) : " + str(self.collision_type[self.collision_type_idx])
    i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    text = "Hide After Creation (H) : " + str(scene.my_hide)
    i = draw_modal_item(self, font_id, i, vertical_px_offset, text, color_type='scene')

    if self.use_decimation:
        text = "Decimate (D): " + str(self.decimate_amount)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    if self.use_vertex_count:
        text = "Segments (E): " + str(self.vertex_count)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    if self.use_modifier_stack:
        text = "Use Modifier Stack (P) : " + str(self.my_use_modifier_stack)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    if self.use_cylinder_axis:
        text = "Cylinder Axis Alignement (X/Y/Z) : " + str(self.cylinder_axis)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    if self.use_sphere_segments:
        text = "Sphere Segments (W): " + str(self.sphere_segments)
        i = draw_modal_item(self, font_id, i, vertical_px_offset, text)

    if self.use_type_change:
        text="Collider Shape (C): " + str(self.collider_shapes[self.collider_shapes_idx])
        i = draw_modal_item(self, font_id, i, vertical_px_offset, text)



class OBJECT_OT_add_bounding_object():
    """Abstract parent class for modal operators contain common methods and properties for all add bounding object operators"""
    bl_options = {'REGISTER', 'UNDO'}

    bm = []

    @classmethod
    def bmesh(cls, bm):
        cls.bm.append(bm)

    def remove_objects(self, list):
        # Remove previously created collisions
        if len(list) > 0:
            for ob in list:
                objs = bpy.data.objects
                objs.remove(ob, do_unlink=True)

    def custom_set_parent(self, context, parent, child):
        # set parent
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = parent
        parent.select_set(True)
        child.select_set(True)

        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)

    def generate_bounding_box(self, positionsX, positionsY, positionsZ):
        # get the min and max coordinates for the bounding box
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

    def get_vertices_Edit(self, obj, use_modifiers = False):
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
        bpy.ops.object.mode_set(mode='EDIT')
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
            used_edges = me.edges
            used_faces = me.polygons

        if len(used_vertices) == 0:
            return None

        return used_vertices


    def mesh_from_selection(self, obj, use_modifiers = False):

        ''' Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no vertices to return '''
        bpy.ops.object.mode_set(mode='EDIT')
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
            used_edges = me.edges
            used_faces = me.polygons

        if len(used_vertices) == 0:
            return None

        return used_vertices

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

    def set_viewport_drawing(self, context, bounding_object):
        ''' Assign material to the bounding object and set the visibility settings of the created object.'''
        bounding_object.display_type = 'SOLID'
        self.set_object_color(bounding_object)

    def set_object_color(self, obj):
        if self.collision_type[self.collision_type_idx] == 'SIMPLE_COMPLEX':
            obj.color = self.prefs.my_color_all
        elif self.collision_type[self.collision_type_idx] == 'SIMPLE':
            obj.color = self.prefs.my_color_simple
        elif self.collision_type[self.collision_type_idx] == 'COMPLEX':
            obj.color = self.prefs.my_color_complex

    def set_object_type(self, obj):
        obj['collider_type'] = self.collision_type[self.collision_type_idx]

    def get_complexity_suffix(self):

        if self.collision_type[self.collision_type_idx] == 'SIMPLE_COMPLEX':
            suffix = self.prefs.colAll
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

    def create_name_number(self, name, nr):
        nr = str('_{num:{fill}{width}}'.format(num=(nr), fill='0', width=3))
        return name + nr

    def unique_name(self, name):
        '''recursive function to find unique name'''
        new_name = self.create_name_number(name, self.name_count)

        while new_name in bpy.data.objects:
            self.name_count = self.name_count + 1
            new_name = self.create_name_number(name, self.name_count)

        self.name_count = self.name_count + 1
        return new_name

    def collider_name(self, basename = 'Basename'):
        separator = self.prefs.separator

        if self.prefs.use_parent_name:
            name = basename
        else:
            name = self.prefs.basename

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
        modifier.strength = self.displace_my_offset
        self.displace_modifiers.append(modifier)

    def del_displace_modifier(self,context,bounding_object):
        if bounding_object.modifiers.get('Collision_displace'):
            mod = bounding_object.modifiers['Collision_displace']
            bounding_object.modifiers.remove(mod)

    def add_decimate_modifier(self, context, bounding_object):
        scene = context.scene

        # add decimation modifier and safe it to manipulate the strenght in the modal operator
        modifier = bounding_object.modifiers.new(name="Collision_decimate", type='DECIMATE')
        modifier.ratio = self.decimate_amount
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


    def __init__(self):
        # has to be in --init
        self.vertex_count = 8
        self.use_decimation = False
        self.use_vertex_count = False
        self.use_modifier_stack = False
        self.use_space = False
        self.use_cylinder_axis = False
        self.use_global_local_switches = False
        self.use_sphere_segments = False
        self.type_suffix = ''
        self.use_type_change = False

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def invoke(self, context, event):

        global collider_types

        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

        # get collision suffix from preferences
        self.prefs = context.preferences.addons["CollisionHelpers"].preferences
        scene = context.scene

        # Active object
        if context.object is None:
            context.view_layer.objects.active = context.selected_objects[0]
        context.object.select_set(True)

        # INITIAL STATE
        self.selected_objects = context.selected_objects.copy()
        self.active_obj = context.view_layer.objects.active
        self.obj_mode = context.object.mode

        # MODIFIERS
        self.my_use_modifier_stack = False
        self.displace_active = False
        self.displace_modifiers = []
        self.displace_my_offset = 0.0
        self.decimate_active = False
        self.decimate_modifiers = []
        self.decimate_amount = 1.0
        self.opacity_active = False
        self.cylinder_axis = 'Z'
        self.vertex_count_active = False
        self.sphere_segments_active = False
        self.color_type = context.space_data.shading.color_type
        self.shading_idx = 0
        self.shading_modes = ['OBJECT','MATERIAL','SINGLE']
        self.collision_type_idx = 0
        self.collision_type = collider_types
        #sphere
        self.sphere_segments = 16

        # store mouse position
        self.first_mouse_x = event.mouse_x
        self.physics_material_name = scene.CollisionMaterials
        self.new_colliders_list = []

        self.name_count = 1

        # Set up scene
        if context.space_data.shading.type == 'SOLID':
            context.space_data.shading.color_type = self.shading_modes[self.shading_idx]

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

        delta = self.first_mouse_x - event.mouse_x

        # User Input
        # aboard operator
        if event.type in {'RIGHTMOUSE', 'ESC'}:

            # Remove previously created collisions
            if self.new_colliders_list != None:
                for obj in self.new_colliders_list:
                    objs = bpy.data.objects
                    objs.remove(obj, do_unlink=True)

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
                if self.displace_my_offset == 0.0:
                    self.del_displace_modifier(context,obj)
                if self.decimate_amount == 1.0:
                    self.del_decimate_modifier(context,obj)

                obj.display_type = scene.my_collision_shading_view
                if scene.my_hide:
                    obj.hide_viewport = scene.my_hide

            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except ValueError:
                pass

            bpy.ops.object.mode_set(mode='OBJECT')

            return {'FINISHED'}

        # hide after creation
        elif event.type == 'H' and event.value == 'RELEASE':
            scene.my_hide = not scene.my_hide
            self.execute(context)

        elif event.type == 'S' and event.value == 'RELEASE':
            self.displace_active = not self.displace_active
            self.opacity_active = False
            self.decimate_active = False
            self.vertex_count_active = False
            self.sphere_segments_active = False

        elif event.type == 'D' and event.value == 'RELEASE':
            self.decimate_active = not self.decimate_active
            self.opacity_active = False
            self.displace_active = False
            self.vertex_count_active = False
            self.sphere_segments_active = False

        elif event.type == 'A' and event.value == 'RELEASE':
            self.opacity_active = not self.opacity_active
            self.displace_active = False
            self.decimate_active = False
            self.vertex_count_active = False
            self.sphere_segments_active = False

        elif event.type == 'E' and event.value == 'RELEASE':
            self.vertex_count_active = not self.vertex_count_active
            self.displace_active = False
            self.decimate_active = False
            self.opacity_active = False
            self.sphere_segments_active = False

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
            if self.displace_active:
                for mod in self.displace_modifiers:
                    strenght = 1.0 - delta * 0.01
                    mod.strength = strenght
                    mod.show_on_cage = True
                    mod.show_in_editmode = True

                    # Store displacement strenght to use when regenerating the colliders
                    self.displace_my_offset = mod.strength

            if self.decimate_active:
                for mod in self.decimate_modifiers:
                    dec_amount = 1.0 - delta * 0.005
                    mod.ratio = dec_amount
                    # mod.show_on_cage = True
                    # mod.show_in_editmode = True

                    # Store displacement strenght to use when regenerating the colliders
                    self.decimate_amount = mod.ratio

            if self.opacity_active:
                color_alpha = 0.5 + delta * 0.005

                for obj in self.new_colliders_list:
                    obj.color[3] = color_alpha

                scene.my_color[3] = color_alpha

            if self.vertex_count_active:
                if event.ctrl:
                    vertex_count = abs(int(round((12 + delta * 0.15))))
                elif event.shift:
                    vertex_count = abs(int(round((12 + delta * 0.002))))
                else:
                    vertex_count = abs(int(round((12 + delta * 0.02))))

                # check if value changed to avoid regenerating collisions for the same value
                if vertex_count != int(round(self.vertex_count)):
                    self.vertex_count = vertex_count
                    self.execute(context)

            if self.sphere_segments_active:
                if event.ctrl:
                    segments = int(abs(round((16 + delta * 0.15))))
                elif event.shift:
                    segments = int(abs(round((16 + delta * 0.002))))
                else:
                    segments = int(abs(round((16 + delta * 0.02))))

                    # check if value changed to avoid regenerating collisions for the same value
                if segments != int(round(self.sphere_segments)):
                    self.sphere_segments = segments
                    self.execute(context)

        # passthrough specific events to blenders default behavior
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

    def execute(self, context):
        #reset naming count:
        self.name_count = 1
        self.obj_mode = context.object.mode

        self.remove_objects(self.new_colliders_list)
        self.new_colliders_list = []

        # reset previously stored displace modifiers when creating a new object
        self.displace_modifiers = []

        # Create the bounding geometry, depending on edit or object mode.
        self.old_objs = set(context.scene.objects)


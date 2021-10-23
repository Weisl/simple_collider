import bgl
import blf
import bpy
import gpu

from ..pyshics_materials.material_functions import remove_materials, set_material

collider_types = ['SIMPLE_COMPLEX','SIMPLE', 'COMPLEX']

def draw_viewport_overlay(self, context):
    scene = context.scene
    font_id = 0  # XXX, need to find out how best to get this.
    vertical_px_offset = 30
    i = 1

    if self.use_space:
        # draw some text
        global_orient = "ON" if scene.my_space == 'GLOBAL' else "OFF"
        blf.position(font_id, 30, i *vertical_px_offset, 0)
        blf.size(font_id, 20, 72)
        blf.draw(font_id, "Global Orient (G): " + global_orient)
        i += 1

        # draw some text
        local_orient = "ON" if scene.my_space == 'LOCAL' else "OFF"
        blf.position(font_id, 30, i*vertical_px_offset, 0)
        blf.size(font_id, 20, 72)
        blf.draw(font_id, "Local Orient (L): " + local_orient)
        i += 1

    blf.position(font_id, 30, i*vertical_px_offset, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Shrink/Inflate (S): " + str(self.displace_my_offset))
    i += 1

    blf.position(font_id, 30, i*vertical_px_offset, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Opacity (A) : " + str(scene.my_color[3]))
    i += 1

    blf.position(font_id, 30, i*vertical_px_offset, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Preview View (V) : " + self.shading_modes[self.shading_idx])
    i += 1

    blf.position(font_id, 30, i*vertical_px_offset, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Collider Type (T) : " + str(self.collision_type[self.collision_type_idx]))
    i += 1

    blf.position(font_id, 30, i*vertical_px_offset, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Hide After Creation (H) : " + str(scene.my_hide))
    i += 1

    if self.use_decimation:
        blf.position(font_id, 30, i * vertical_px_offset, 0)
        blf.size(font_id, 20, 72)
        blf.draw(font_id, "Decimate (D): " + str(self.decimate_amount))
        i += 1

    if self.use_vertex_count:
        blf.position(font_id, 30, i * vertical_px_offset, 0)
        blf.size(font_id, 20, 72)
        blf.draw(font_id, "Segments (E): " + str(self.vertex_count))
        i += 1

    if self.use_modifier_stack:
        blf.position(font_id, 30, i * vertical_px_offset, 0)
        blf.size(font_id, 20, 72)
        blf.draw(font_id, "Use Modifier Stack (P) : " + str(self.my_use_modifier_stack))
        i += 1

    if self.use_cylinder_axis:
        blf.position(font_id, 30, i * vertical_px_offset, 0)
        blf.size(font_id, 20, 72)
        blf.draw(font_id, "Cylinder Axis Alignement (X/Y/Z) : " + str(self.cylinder_axis))
        i += 1

    if self.use_sphere_segments:
        blf.position(font_id, 30, i * vertical_px_offset, 0)
        blf.size(font_id, 20, 72)
        blf.draw(font_id, "Sphere Segments (W): " + str(self.sphere_segments))
        i += 1

    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(2)
    shader.bind()
    shader.uniform_float("color", (1.0, 1.0, 1.0, 0.5))

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)


class OBJECT_OT_add_bounding_object():
    """Abstract parent class to contain common methods and properties for all add bounding object operators"""
    bl_options = {'REGISTER', 'UNDO'}

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

    def get_vertices(self, bm, me, preselect_all=False):
        ''' Get vertices from the bmesh. Returns a list of all or selected vertices. Returns None if there are no vertices to return '''
        me.update() # update mesh data. This is needed to get the current mesh data after editing the mesh (adding, deleting, transforming)

        if preselect_all == True:
            used_vertices = bm.verts
        else:
            used_vertices = [v for v in bm.verts if v.select]

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

    def primitive_postprocessing(self, context, bounding_object, base_object_collections, physics_material_name):

        self.set_viewport_drawing(context, bounding_object)
        self.add_displacement_modifier(context, bounding_object)
        self.set_collections(bounding_object, base_object_collections)

        if self.prefs.use_col_collection:
            collection_name = self.prefs.col_collection_name
            self.add_to_collections(bounding_object, collection_name)

        if self.use_decimation:
            self.add_decimate_modifier(context, bounding_object)

        self.set_physics_material(context, bounding_object, physics_material_name)

        bounding_object['isCollider'] = True
        bounding_object['collider_type'] = self.collision_type[self.collision_type_idx]

    def set_viewport_drawing(self, context, bounding_object):
        ''' Assign material to the bounding object and set the visibility settings of the created object.'''
        bounding_object.display_type = 'SOLID'
        self.set_object_color(context, bounding_object)

    def set_object_color(self, context, obj):
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

        name_pre_suffix = self.prefs.colPreSuffix + separator + self.get_complexity_suffix() + separator + self.type_suffix + separator + self.prefs.optionalSuffix

        if self.prefs.naming_position == 'SUFFIX':
            new_name = basename + separator + name_pre_suffix
        else: #self.prefs.naming_position == 'PREFIX'
            new_name = name_pre_suffix + separator + basename

        print("collider_name FUNCTION: " + str(new_name))
        return self.unique_name(new_name)

    def update_name(self):
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
    def set_physics_material(self, context, bounding_object, physics_material_name):
        remove_materials(bounding_object)
        set_material(bounding_object, physics_material_name)

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
                self.set_object_color(context,obj)
                self.set_object_type(obj)
                self.update_name()
                # print('collision type = %s' % (str(self.collision_type[(self.collision_type_idx)])))

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


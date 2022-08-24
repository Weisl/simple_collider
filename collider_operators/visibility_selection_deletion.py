import bpy
from ..groups.user_groups import default_groups_enum

class COLLISION_OT_Selection(bpy.types.Operator):
    """Select collider objects"""
    bl_idname = "object.select_collisions"
    bl_label = "Select collider objects"
    bl_description = 'Select colliders or objects of type: '
    bl_options = {"REGISTER", "UNDO"}

    select: bpy.props.BoolProperty(
        name='Select/Un-Select',
        default=True
    )

    mode: bpy.props.EnumProperty(items=default_groups_enum,
                                 name='Collider Group',
                                 default='ALL_COLLIDER'
                                 )

    def execute(self, context):
        scene = context.scene
        count = 0

        if self.select:
            for ob in bpy.context.view_layer.objects:
                if self.mode == 'ALL_COLLIDER':
                    if ob.get('isCollider') == True:
                        count += 1
                        ob.select_set(self.select)
                    else:
                        ob.select_set(not self.select)

                elif self.mode == 'OBJECTS':
                    if not ob.get('isCollider'):
                        count += 1
                        ob.select_set(self.select)
                    else:
                        ob.select_set(not self.select)

                else:  # if self.mode == 'USER_02' or self.mode == 'USER_03'
                    if ob.get('isCollider') and ob.get('collider_type') == self.mode:
                        count += 1
                        ob.select_set(self.select)
                    else:
                        ob.select_set(not self.select)

        else:  # self.select = False
            for ob in bpy.context.view_layer.objects:
                if self.mode == 'ALL_COLLIDER':
                    if ob.get('isCollider') == True:
                        count += 1
                        ob.select_set(self.select)
                elif self.mode == 'OBJECTS':
                    if not ob.get('isCollider'):
                        count += 1
                        ob.select_set(self.select)
                else:  # if self.mode == 'USER_02' or self.mode == 'USER_03'
                    if ob.get('isCollider') and ob.get('collider_type') == self.mode:
                        count += 1
                        ob.select_set(self.select)

        if count == 0:
            if self.select:
                self.report({'INFO'}, 'No objects to select.')
            else:
                self.report({'INFO'}, 'No objects to deselect.')
            return {'CANCELLED'}

        return {'FINISHED'}


class COLLISION_OT_simple_select(COLLISION_OT_Selection):
    bl_idname = "object.simple_select_collisions"
    bl_label = "Select Simple Colliders"
    bl_description = 'Select all colliders that are assigned to user group 01'


class COLLISION_OT_complex_select(COLLISION_OT_Selection):
    bl_idname = "object.complex_select_collisions"
    bl_label = "Select Complex Colliders"
    bl_description = 'Select all objects that are defined as complex colliders'


class COLLISION_OT_simple_complex_select(COLLISION_OT_Selection):
    bl_idname = "object.simple_complex_select_collisions"
    bl_label = "Select Simple and Complex Colliders"
    bl_description = 'Select all objects that are defined as simple and complex colliders'


class COLLISION_OT_all_select(COLLISION_OT_Selection):
    bl_idname = "object.all_select_collisions"
    bl_label = "Select all Colliders"
    bl_description = 'Select all collider objects: Simple, Complex, Simple and Complex.'


class COLLISION_OT_non_collider_select(COLLISION_OT_Selection):
    bl_idname = "object.non_collider_select_collisions"
    bl_label = "Select non Colliders"
    bl_description = 'Select all objects that are not colliders.'


class COLLISION_OT_Deletion(bpy.types.Operator):
    """Delete collider objects"""
    bl_idname = "object.delete_collisions"
    bl_label = "Delete collider objects"
    bl_description = 'Delete collision objects of type:'
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(items=default_groups_enum,
                                 name='Collider Group',
                                 default='ALL_COLLIDER'
                                 )

    def execute(self, context):
        objects_to_remove = []

        for ob in bpy.context.view_layer.objects:
            # if ob.parent in selected_objs:
            if self.mode == 'ALL_COLLIDER':
                if ob.get('isCollider') == True:
                    objects_to_remove.append(ob)

            elif self.mode == 'OBJECTS':
                if not ob.get('isCollider'):
                    objects_to_remove.append(ob)

            elif ob.get('isCollider') and ob.get('collider_type') == self.mode:
                objects_to_remove.append(ob)

        if len(objects_to_remove) == 0:
            self.report({'INFO'}, 'No objects to delete.')

        # Call the delete oparator
        else:
            for obj in objects_to_remove:
                bpy.data.objects.remove(obj, do_unlink=True)

        return {'FINISHED'}


class COLLISION_OT_simple_delete(COLLISION_OT_Deletion):
    bl_idname = "object.simple_delete_collisions"
    bl_label = "Delete Simple Colliders"
    bl_description = 'Delete all objects that are defined as simple colliders'


class COLLISION_OT_complex_delete(COLLISION_OT_Deletion):
    bl_idname = "object.complex_delete_collisions"
    bl_label = "Delete Complex Colliders"
    bl_description = 'Delete all objects that are defined as complex colliders'


class COLLISION_OT_simple_complex_delete(COLLISION_OT_Deletion):
    bl_idname = "object.simple_complex_delete_collisions"
    bl_label = "Delete Simple and Complex Colliders"
    bl_description = 'Delete all objects that are defined as simple and complex colliders'


class COLLISION_OT_all_delete(COLLISION_OT_Deletion):
    bl_idname = "object.all_delete_collisions"
    bl_label = "Delete all Colliders"
    bl_description = 'Delete all collider objects: Simple, Complex, Simple and Complex.'


class COLLISION_OT_non_collider_delete(COLLISION_OT_Deletion):
    bl_idname = "object.non_collider_delete_collisions"
    bl_label = "Delete non Colliders"
    bl_description = 'Delete all objects that are not colliders.'


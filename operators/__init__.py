import bpy

from . import add_bounding_box
from . import add_bounding_convex_hull
from . import add_bounding_cylinder
from . import add_bounding_primitive
from . import add_bounding_sphere
from . import add_collision_mesh
from . import add_minimum_bounding_box
from . import conversion_operators
from . import visibility_selection_deletion
from . import visibility_settings

default_groups_dic = {
    'ALL_COLLIDER': 'Colliders',
    'OBJECTS': "Non Colliders",
    'SIMPLE_COMPLEX': 'Simple and Complex',
    'SIMPLE': 'Simple',
    'COMPLEX': 'Complex',
}


def update_hidden(self, context):
    print("self.hidden = " + str(self.hidden))
    for ob in bpy.data.objects:
        if ob.get('isCollider'):
            ob.hide_viewport = self.hidden
    self.hidden = not self.hidden


def update_selected(self, context):
    print("self.selected = " + str(self.selected))
    for ob in bpy.data.objects:
        if ob.get('isCollider'):
            ob.select_set(self.selected)
        else:
            ob.select_set(not self.selected)
    self.selected = not self.selected


class ColliderGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default='Group')
    identifier: bpy.props.StringProperty(default='Group')
    hidden: bpy.props.BoolProperty(default=True, update=update_hidden)
    selected: bpy.props.BoolProperty(default=False, update=update_selected)

    show_icon = bpy.props.StringProperty(default='HIDE_OFF')
    hide_icon = bpy.props.StringProperty(default='HIDE_ON')
    show_text = bpy.props.StringProperty(default='')
    hide_text = bpy.props.StringProperty(default='')

    select_icon = bpy.props.StringProperty(default='NONE')
    deselect_icon = bpy.props.StringProperty(default='NONE')
    select_text = bpy.props.StringProperty(default='Select')
    deselect_text = bpy.props.StringProperty(default='Deselect')

    delete_icon = bpy.props.StringProperty(default='TRASH')
    delete_text = bpy.props.StringProperty(default='')


classes = (
    ColliderGroup,
    add_bounding_box.OBJECT_OT_add_bounding_box,
    add_minimum_bounding_box.OBJECT_OT_add_aligned_bounding_box,
    add_bounding_cylinder.OBJECT_OT_add_bounding_cylinder,
    add_bounding_sphere.OBJECT_OT_add_bounding_sphere,
    add_bounding_convex_hull.OBJECT_OT_add_convex_hull,
    add_collision_mesh.OBJECT_OT_add_mesh_collision,
    visibility_selection_deletion.COLLISION_OT_Visibility,
    visibility_selection_deletion.COLLISION_OT_Selection,
    conversion_operators.OBJECT_OT_convert_to_collider,
    conversion_operators.OBJECT_OT_convert_to_mesh,
    visibility_selection_deletion.COLLISION_OT_Deletion,
    visibility_selection_deletion.COLLISION_OT_simple_select,
    visibility_selection_deletion.COLLISION_OT_simple_deselect,
    visibility_selection_deletion.COLLISION_OT_simple_delete,
    visibility_selection_deletion.COLLISION_OT_complex_select,
    visibility_selection_deletion.COLLISION_OT_complex_deselect,
    visibility_selection_deletion.COLLISION_OT_complex_delete,
    visibility_selection_deletion.COLLISION_OT_simple_complex_select,
    visibility_selection_deletion.COLLISION_OT_simple_complex_deselect,
    visibility_selection_deletion.COLLISION_OT_simple_complex_delete,
    visibility_selection_deletion.COLLISION_OT_all_select,
    visibility_selection_deletion.COLLISION_OT_all_deselect,
    visibility_selection_deletion.COLLISION_OT_all_delete,
    visibility_selection_deletion.COLLISION_OT_non_collider_select,
    visibility_selection_deletion.COLLISION_OT_non_collider_deselect,
    visibility_selection_deletion.COLLISION_OT_non_collider_delete,
    visibility_selection_deletion.COLLISION_OT_simple_show,
    visibility_selection_deletion.COLLISION_OT_simple_hide,
    visibility_selection_deletion.COLLISION_OT_complex_show,
    visibility_selection_deletion.COLLISION_OT_complex_hide,
    visibility_selection_deletion.COLLISION_OT_simple_complex_show,
    visibility_selection_deletion.COLLISION_OT_simple_complex_hide,
    visibility_selection_deletion.COLLISION_OT_all_show,
    visibility_selection_deletion.COLLISION_OT_all_hide,
    visibility_selection_deletion.COLLISION_OT_non_collider_show,
    visibility_selection_deletion.COLLISION_OT_non_collider_hide,
    visibility_selection_deletion.COLLISION_OT_toggle_collider_visibility,
    visibility_settings.VIEW3D_OT_object_view,
    visibility_settings.VIEW3D_OT_material_view,
)


def update_display_colliders(self, context):
    for obj in bpy.data.objects:
        if obj.get('isCollider'):
            obj.display_type = self.display_type
    return {'FINISHED'}


def register():
    scene = bpy.types.Scene
    obj = bpy.types.Object

    # Display setting of the bounding object in the viewport
    scene.my_hide = bpy.props.BoolProperty(name="Hide After Creation",
                                           description="Hide Bounding Object After Creation.", default=False)

    # Display setting of the bounding object in the viewport
    scene.visibility_toggle_all = bpy.props.BoolProperty(name="Toggle Visibility",
                                                         description="", default=False)

    scene.my_collision_shading_view = bpy.props.EnumProperty(name="Display",
                                                             description='How to display the collision in the viewport.',
                                                             items=(
                                                                 ('SOLID', "Solid", "Display the collider as a solid."),
                                                                 (
                                                                     'WIRE', "Wire",
                                                                     "Display the collider as a wireframe"),
                                                                 ('BOUNDS', "Bounds",
                                                                  "Display the bounds of the collider")),
                                                             default="SOLID")

    # Tranformation space to be used for creating the bounding object.
    scene.my_space = bpy.props.EnumProperty(name="Generation Axis",
                                            items=(('LOCAL', "Local",
                                                    "Generate the collision based on the local space of the object vertices."),
                                                   ('GLOBAL', "Global",
                                                    "Generate the collision based on the global space of the object vertices.")),
                                            default="LOCAL")

    scene.display_type = bpy.props.EnumProperty(name="Collider Display",
                                                items=(
                                                    # ('TEXTURED', "Textured", "Display the colliders with textures"),
                                                    ('SOLID', "Solid", "Display the colliders as solid"),
                                                    ('WIRE', "Wire", "Display the colliders as wireframe"),
                                                    # ('BOUNDS', "Bounds", "Display the bounds of the the colliders")
                                                ),
                                                default="SOLID",
                                                update=update_display_colliders)

    scene.wireframe_mode = bpy.props.EnumProperty(name="Wireframe Mode",
                                                  items=(('OFF', "Off",
                                                          "There is no wireframe preview on the collision mesh."),
                                                         ('PREVIEW', "Preview",
                                                          "The wireframes are only visible during the generation."),
                                                         ('ALWAYS', "Always",
                                                          "The wireframes remain visible afterwards.")),
                                                  description="Hide Bounding Object After Creation.", default='PREVIEW')

    # OBJECT
    obj.basename = bpy.props.StringProperty(default='geo', name='Basename',
                                            description='Default naming used for collisions when the name is not inherited from a parent (Name from parent is disabled).')

    obj.collider_type = bpy.props.EnumProperty(name="Shading",
                                               items=[('BOX', "Box", "Used to descibe boxed shape collision shapes."),
                                                      (
                                                          'SHERE', "Sphere",
                                                          "Used to descibe spherical collision shapes."),
                                                      ('CONVEX', "CONVEX",
                                                       "Used to descibe convex shaped collision shapes."),
                                                      ('MESH', "Triangle Mesh",
                                                       "Used to descibe complex triangle mesh collisions.")],
                                               default='BOX')

    obj.collider_complexity = bpy.props.EnumProperty(name="collider complexity", items=[
        ('SIMPLE_COMPLEX', "Simple Complex",
         "(Simple and Complex) Custom value to distinguish different types of collisions in a game engine."),
        ('SIMPLE', "Simple", "(Simple) Custom value to distinguish different types of collisions in a game engine."),
        (
            'COMPLEX', "Complex",
            "(Complex) Custom value to distinguish different types of collisions in a game engine.")],
                                                     default="SIMPLE_COMPLEX")

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    scene.visibility_toggle = default_groups_dic

    # # Pointer Properties have to be initialized after classes
    scene.visibility_toggle_all = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_obj = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_complex_simple = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_complex = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_simple = bpy.props.PointerProperty(type=ColliderGroup)


def unregister():
    scene = bpy.types.Scene
    obj = bpy.types.Object

    del scene.visibility_toggle_simple
    del scene.visibility_toggle_complex
    del scene.visibility_toggle_complex_simple
    del scene.visibility_toggle_obj
    del scene.visibility_toggle_all
    del scene.visibility_toggle

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # delete custom properties on unregister
    del scene.my_collision_shading_view
    del scene.my_space
    del scene.my_hide
    del scene.wireframe_mode
    del scene.visible

    del obj.basename
    del obj.collider_type
    del obj.collider_complexity

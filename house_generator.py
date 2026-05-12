import bpy
import bmesh
import math
from mathutils import Vector, Color

# Constants
FT_TO_M = 0.3048
WIDTH = 18 * FT_TO_M  # Frontage (East)
DEPTH = 42 * FT_TO_M  # Depth (East to West)
WALL_THICKNESS = 0.23
FLOOR_HEIGHT = 3.0

def create_collection(name):
    if name not in bpy.data.collections:
        new_col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(new_col)
    return bpy.data.collections[name]

def create_wall(name, start, end, height, thickness, collection):
    mid_point = (start + end) / 2
    direction = end - start
    length = direction.length
    angle = math.atan2(direction.y, direction.x)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(mid_point.x, mid_point.y, mid_point.z + height/2))
    wall = bpy.context.active_object
    wall.name = name
    wall.scale = (length, thickness, height)
    wall.rotation_euler[2] = angle

    # Move to collection
    for col in wall.users_collection:
        col.objects.unlink(wall)
    collection.objects.link(wall)
    return wall

def create_floor(name, x, y, w, d, thickness, z_level, collection):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + w/2, y + d/2, z_level - thickness/2))
    floor = bpy.context.active_object
    floor.name = name
    floor.scale = (w, d, thickness)

    for col in floor.users_collection:
        col.objects.unlink(floor)
    collection.objects.link(floor)
    return floor

def setup_materials():
    materials = {}

    # Sandstone with Brick Pattern
    mat_sandstone = bpy.data.materials.new(name="Sandstone")
    mat_sandstone.use_nodes = True
    nodes = mat_sandstone.node_tree.nodes
    nodes.clear()
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_pbsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_pbsdf.inputs['Base Color'].default_value = (0.8, 0.7, 0.5, 1.0)

    node_brick = nodes.new(type='ShaderNodeTexBrick')
    node_brick.inputs['Scale'].default_value = 10.0
    node_brick.inputs['Color1'].default_value = (0.8, 0.7, 0.5, 1.0)
    node_brick.inputs['Color2'].default_value = (0.75, 0.65, 0.45, 1.0)
    node_brick.inputs['Mortar'].default_value = (0.3, 0.3, 0.3, 1.0)

    mat_sandstone.node_tree.links.new(node_brick.outputs['Color'], node_pbsdf.inputs['Base Color'])
    mat_sandstone.node_tree.links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    materials['Sandstone'] = mat_sandstone

    # Marble with Tiles
    mat_marble = bpy.data.materials.new(name="Marble")
    mat_marble.use_nodes = True
    nodes = mat_marble.node_tree.nodes
    nodes.clear()
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_pbsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_pbsdf.inputs['Base Color'].default_value = (0.9, 0.9, 0.9, 1.0)
    node_pbsdf.inputs['Roughness'].default_value = 0.1

    node_noise = nodes.new(type='ShaderNodeTexNoise')
    node_noise.inputs['Scale'].default_value = 10.0
    node_noise.inputs['Detail'].default_value = 15.0

    node_brick = nodes.new(type='ShaderNodeTexBrick')
    node_brick.inputs['Scale'].default_value = 5.0
    node_brick.inputs['Mortar Size'].default_value = 0.01

    node_mix = nodes.new(type='ShaderNodeMix')
    node_mix.data_type = 'RGBA'
    node_mix.blend_type = 'MIX'
    mat_marble.node_tree.links.new(node_noise.outputs['Fac'], node_mix.inputs[6])
    mat_marble.node_tree.links.new(node_brick.outputs['Fac'], node_mix.inputs[7])

    mat_marble.node_tree.links.new(node_mix.outputs[2], node_pbsdf.inputs['Base Color'])
    mat_marble.node_tree.links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    materials['Marble'] = mat_marble

    # Wood
    mat_wood = bpy.data.materials.new(name="Wood")
    mat_wood.use_nodes = True
    nodes = mat_wood.node_tree.nodes
    nodes.clear()
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_pbsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_pbsdf.inputs['Base Color'].default_value = (0.3, 0.15, 0.05, 1.0)
    node_pbsdf.inputs['Roughness'].default_value = 0.4
    node_wave = nodes.new(type='ShaderNodeTexWave')
    node_wave.inputs['Scale'].default_value = 20.0
    mat_wood.node_tree.links.new(node_wave.outputs['Color'], node_pbsdf.inputs['Base Color'])
    mat_wood.node_tree.links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    materials['Wood'] = mat_wood

    # Glass
    mat_glass = bpy.data.materials.new(name="Glass")
    mat_glass.use_nodes = True
    nodes = mat_glass.node_tree.nodes
    nodes.clear()
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_pbsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_pbsdf.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    node_pbsdf.inputs['Transmission Weight'].default_value = 1.0
    node_pbsdf.inputs['IOR'].default_value = 1.45
    node_pbsdf.inputs['Roughness'].default_value = 0.0
    mat_glass.node_tree.links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    materials['Glass'] = mat_glass

    # Rubber (Gym floor)
    mat_rubber = bpy.data.materials.new(name="Rubber")
    mat_rubber.use_nodes = True
    nodes = mat_rubber.node_tree.nodes
    nodes.clear()
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_pbsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_pbsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1.0)
    node_pbsdf.inputs['Roughness'].default_value = 0.9
    mat_rubber.node_tree.links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    materials['Rubber'] = mat_rubber

    # RGB (Gaming)
    mat_rgb = bpy.data.materials.new(name="RGB")
    mat_rgb.use_nodes = True
    nodes = mat_rgb.node_tree.nodes
    nodes.clear()
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_emit = nodes.new(type='ShaderNodeEmission')
    node_emit.inputs['Color'].default_value = (0.0, 0.8, 1.0, 1.0) # Cyan
    node_emit.inputs['Strength'].default_value = 5.0
    mat_rgb.node_tree.links.new(node_emit.outputs['Emission'], node_output.inputs['Surface'])
    materials['RGB'] = mat_rgb

    # Green for Plants
    mat_green = bpy.data.materials.new(name="PlantGreen")
    mat_green.use_nodes = True
    nodes = mat_green.node_tree.nodes
    nodes.clear()
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_pbsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_pbsdf.inputs['Base Color'].default_value = (0.1, 0.5, 0.1, 1.0)
    mat_green.node_tree.links.new(node_pbsdf.outputs['BSDF'], node_output.inputs['Surface'])
    materials['Green'] = mat_green

    return materials

def create_furniture_primitive(name, location, scale, material, collection):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if material:
        obj.data.materials.append(material)
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)
    return obj

def create_sofa(name, location, scale, mats, collection):
    # Base
    create_furniture_primitive(f"{name}_Base", location, scale, mats['Wood'], collection)
    # Backrest
    back_loc = Vector(location) + Vector((0, scale.y/2, scale.z/2))
    create_furniture_primitive(f"{name}_Back", back_loc, (scale.x, 0.1, scale.z), mats['Wood'], collection)

def create_table(name, location, scale, mats, collection):
    # Top
    create_furniture_primitive(f"{name}_Top", location, scale, mats['Wood'], collection)
    # Legs
    leg_offset_x = scale.x / 2 - 0.05
    leg_offset_y = scale.y / 2 - 0.05
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            leg_loc = Vector(location) - Vector((0, 0, scale.z/2 + 0.35)) + Vector((sx * leg_offset_x, sy * leg_offset_y, 0))
            create_furniture_primitive(f"{name}_Leg", leg_loc, (0.1, 0.1, 0.7), mats['Wood'], collection)

def add_furniture_gf(mats, collection):
    # Otla (Front Platform)
    create_furniture_primitive("GF_Otla", (WIDTH+1, DEPTH-2, 0.2), (2, 4, 0.4), mats['Sandstone'], collection)
    # Living Room Sofa (East side)
    create_sofa("GF_Sofa_Main", (WIDTH-2, DEPTH-5, 0.4), (3, 0.8, 0.6), mats, collection)
    # TV Unit
    create_furniture_primitive("GF_TV_Unit", (WIDTH-0.2, DEPTH-5, 1.2), (0.1, 2, 1.5), mats['Wood'], collection)
    # Pooja Mandir (NE)
    create_furniture_primitive("GF_Pooja", (WIDTH-1, DEPTH-1, 0.6), (1, 1, 1.2), mats['Marble'], collection)
    # Dining Table
    create_table("GF_Dining_Table", (WIDTH-5, DEPTH/2, 0.75), (1.5, 1, 0.05), mats, collection)
    # Kitchen Cabinets (SE)
    create_furniture_primitive("GF_Kitchen_Counter", (WIDTH-1.5, 2, 0.9), (1, 4, 0.1), mats['Marble'], collection)
    # Bed SW Bedroom
    create_furniture_primitive("GF_Bed_SW", (2, 2, 0.3), (2, 2, 0.5), mats['Wood'], collection)
    # Staircase (SW)
    for i in range(15):
        create_furniture_primitive(f"GF_Step_{i}", (1, 5 + i*0.25, i*0.2), (1.5, 0.3, 0.1), mats['Marble'], collection)

def add_furniture_ff(mats, collection):
    # Master Bed (SW)
    create_furniture_primitive("FF_Master_Bed", (2, 2, FLOOR_HEIGHT + 0.3), (2, 2, 0.5), mats['Wood'], collection)
    # Balcony Railing (East)
    create_jali((WIDTH, DEPTH/2, FLOOR_HEIGHT + 1), Vector((0.1, DEPTH, 2)), collection, mats)

def add_furniture_tf(mats, collection):
    # Luxury Room Bed
    create_furniture_primitive("TF_Bed", (WIDTH/2, DEPTH-5, 2*FLOOR_HEIGHT + 0.3), (2, 2, 0.5), mats['Wood'], collection)
    # Gaming Desk
    create_furniture_primitive("TF_Desk", (WIDTH-1, DEPTH-5, 2*FLOOR_HEIGHT + 0.75), (0.8, 2, 0.05), mats['Wood'], collection)
    # Monitor (RGB)
    create_furniture_primitive("TF_Monitor", (WIDTH-0.8, DEPTH-5, 2*FLOOR_HEIGHT + 1.2), (0.05, 1, 0.6), mats['RGB'], collection)
    # Gym Equipment
    create_furniture_primitive("Gym_Bench", (3, DEPTH/2, 2*FLOOR_HEIGHT + 0.4), (0.5, 1.8, 0.4), mats['Rubber'], collection)
    create_furniture_primitive("Gym_Mirror", (0.1, DEPTH/2, 2*FLOOR_HEIGHT + 1.5), (0.05, 3, 2), mats['Glass'], collection)

def setup_lighting():
    # Clear existing lights
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='LIGHT')
    bpy.ops.object.delete()

    # Sun Light
    bpy.ops.object.light_add(type='SUN', location=(10, 10, 20))
    sun = bpy.context.active_object
    sun.data.energy = 5.0
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))

    # World Sky
    bpy.context.scene.world.use_nodes = True
    nodes = bpy.context.scene.world.node_tree.nodes
    nodes.clear()
    node_out = nodes.new(type='ShaderNodeOutputWorld')
    node_sky = nodes.new(type='ShaderNodeTexSky')
    node_sky.sky_type = 'NISHITA'
    node_sky.sun_elevation = math.radians(20) # Golden hour
    bpy.context.scene.world.node_tree.links.new(node_sky.outputs['Color'], node_out.inputs['Surface'])

def setup_cameras():
    # Isometric
    bpy.ops.object.camera_add(location=(20, -20, 20), rotation=(math.radians(45), 0, math.radians(45)))
    cam_iso = bpy.context.active_object
    cam_iso.name = "Cam_Isometric"
    cam_iso.data.type = 'ORTHO'
    cam_iso.data.ortho_scale = 30

    # Front Elevation
    bpy.ops.object.camera_add(location=(WIDTH/2, -15, 5), rotation=(math.radians(90), 0, 0))
    cam_front = bpy.context.active_object
    cam_front.name = "Cam_Front"

    # Top Down
    bpy.ops.object.camera_add(location=(WIDTH/2, DEPTH/2, 25), rotation=(0, 0, 0))
    cam_top = bpy.context.active_object
    cam_top.name = "Cam_Top"
    cam_top.data.type = 'ORTHO'
    cam_top.data.ortho_scale = 20

    # Walkthrough Path
    bpy.ops.curve.primitive_bezier_circle_add(radius=15, location=(WIDTH/2, DEPTH/2, 5))
    path = bpy.context.active_object
    path.name = "Walkthrough_Path"

    bpy.ops.object.camera_add()
    cam_walk = bpy.context.active_object
    cam_walk.name = "Cam_Walkthrough"

    # Follow path constraint
    con = cam_walk.constraints.new(type='FOLLOW_PATH')
    con.name = "FollowPath"
    con.target = path
    con.use_fixed_location = True

    # Animate follow path
    con.keyframe_insert(data_path="offset_factor", frame=1)
    con.offset_factor = 1.0
    con.keyframe_insert(data_path="offset_factor", frame=250)

    # Keyframes for animation
    cam_walk.data.dof.use_dof = True
    cam_walk.data.dof.focus_distance = 10.0

def apply_bevel(obj, amount=0.01):
    mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = amount
    mod.segments = 3

def create_jali(location, size, collection, mats):
    # Procedural Jali (lattice)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=1, location=location)
    jali = bpy.context.active_object
    jali.name = "Jali"
    jali.rotation_euler[1] = math.radians(90) # Vertical
    jali.scale = size

    # Wireframe modifier for lattice look
    mod = jali.modifiers.new(name="Wireframe", type='WIREFRAME')
    mod.thickness = 0.02

    jali.data.materials.append(mats['Wood'])
    for col in jali.users_collection:
        col.objects.unlink(jali)
    collection.objects.link(jali)
    return jali

def create_architectural_opening(target_wall, location, size, mats, collection, is_door=False):
    # Boolean cut for windows/doors
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    cutter = bpy.context.active_object
    cutter.name = "Cutter"
    cutter.scale = size

    mod = target_wall.modifiers.new(name="Boolean", type='BOOLEAN')
    mod.object = cutter
    mod.operation = 'DIFFERENCE'

    # Hide cutter
    cutter.display_type = 'WIRE'
    cutter.hide_render = True
    cutter.hide_viewport = True

    # Add Frame
    frame_thickness = 0.05
    frame_scale = Vector((size.x + frame_thickness, size.y + frame_thickness, size.z + frame_thickness))
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    frame = bpy.context.active_object
    frame.name = "Frame"
    frame.scale = frame_scale

    # Cut hole in frame
    f_mod = frame.modifiers.new(name="Boolean", type='BOOLEAN')
    f_mod.object = cutter
    f_mod.operation = 'DIFFERENCE'

    frame.data.materials.append(mats['Wood'])
    for col in frame.users_collection:
        col.objects.unlink(frame)
    collection.objects.link(frame)

    # Add Glass
    if not is_door:
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        glass = bpy.context.active_object
        glass.name = "GlassPane"
        glass.scale = Vector((size.x - 0.02, 0.02, size.z - 0.02))
        glass.data.materials.append(mats['Glass'])
        for col in glass.users_collection:
            col.objects.unlink(glass)
        collection.objects.link(glass)

    return cutter

def setup_render_settings():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'

    # Cycles settings
    cycles = scene.cycles
    cycles.device = 'GPU'
    cycles.samples = 1024
    cycles.use_denoising = True

    # Resolution 8K (7680 x 4320)
    scene.render.resolution_x = 7680
    scene.render.resolution_y = 4320
    scene.render.resolution_percentage = 100

    # Try to enable GPU devices
    preferences = bpy.context.preferences
    cycles_preferences = preferences.addons['cycles'].preferences
    cycles_preferences.compute_device_type = 'CUDA' # or 'OPTIX'
    for device in cycles_preferences.get_devices_for_type('CUDA'):
        device.use = True

def generate_full_house():
    # Setup Materials
    mats = setup_materials()

    # Ground Plane
    bpy.ops.mesh.primitive_plane_add(size=100, location=(WIDTH/2, DEPTH/2, -0.01))
    ground = bpy.context.active_object
    ground.name = "GroundPlane"
    ground.data.materials.append(mats['Sandstone'])

    # Setup Collections
    root_col = create_collection("House_Project")
    gf_col = create_collection("GF")
    ff_col = create_collection("FF")
    tf_col = create_collection("TF")
    terr_col = create_collection("Terrace")

    # Ground Floor
    floor_gf = create_floor("GF_Main_Floor", 0, 0, WIDTH, DEPTH, 0.2, 0, gf_col)
    floor_gf.data.materials.append(mats['Marble'])

    # GF Exterior Walls
    w_w = create_wall("GF_Wall_W", Vector((0, 0, 0)), Vector((0, DEPTH, 0)), FLOOR_HEIGHT, WALL_THICKNESS, gf_col)
    w_n = create_wall("GF_Wall_N", Vector((0, DEPTH, 0)), Vector((WIDTH, DEPTH, 0)), FLOOR_HEIGHT, WALL_THICKNESS, gf_col)
    w_s = create_wall("GF_Wall_S", Vector((0, 0, 0)), Vector((WIDTH, 0, 0)), FLOOR_HEIGHT, WALL_THICKNESS, gf_col)
    w_e = create_wall("GF_Wall_E", Vector((WIDTH, 0, 0)), Vector((WIDTH, DEPTH, 0)), FLOOR_HEIGHT, WALL_THICKNESS, gf_col)

    for w in [w_w, w_n, w_s, w_e]:
        w.data.materials.append(mats['Sandstone'])
        apply_bevel(w)

    # Openings
    create_architectural_opening(w_e, (WIDTH, DEPTH-2, 1.2), Vector((0.3, 1.5, 2.1)), mats, gf_col, is_door=True) # Main Door
    # Windows
    create_architectural_opening(w_e, (WIDTH, DEPTH-10, 1.5), Vector((0.3, 2, 1.2)), mats, gf_col)
    create_architectural_opening(w_n, (WIDTH/2, DEPTH, 1.5), Vector((2, 0.3, 1.2)), mats, gf_col)

    # GF Interior Walls
    iw1 = create_wall("GF_Int_Wall_1", Vector((4, 0, 0)), Vector((4, 6, 0)), FLOOR_HEIGHT, 0.115, gf_col)
    iw1.data.materials.append(mats['Sandstone'])

    # GF Interior
    add_furniture_gf(mats, gf_col)

    # FF Exterior
    floor_ff = create_floor("FF_Main_Floor", 0, 0, WIDTH, DEPTH, 0.2, FLOOR_HEIGHT, ff_col)
    floor_ff.data.materials.append(mats['Marble'])
    create_wall("FF_Wall_W", Vector((0, 0, FLOOR_HEIGHT)), Vector((0, DEPTH, FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, ff_col).data.materials.append(mats['Sandstone'])
    create_wall("FF_Wall_N", Vector((0, DEPTH, FLOOR_HEIGHT)), Vector((WIDTH, DEPTH, FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, ff_col).data.materials.append(mats['Sandstone'])
    create_wall("FF_Wall_S", Vector((0, 0, FLOOR_HEIGHT)), Vector((WIDTH, 0, FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, ff_col).data.materials.append(mats['Sandstone'])
    create_wall("FF_Wall_E", Vector((WIDTH, 0, FLOOR_HEIGHT)), Vector((WIDTH, DEPTH, FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, ff_col).data.materials.append(mats['Sandstone'])

    add_furniture_ff(mats, ff_col)

    # TF Exterior
    floor_tf = create_floor("TF_Main_Floor", 0, 0, WIDTH, DEPTH, 0.2, 2*FLOOR_HEIGHT, tf_col)
    floor_tf.data.materials.append(mats['Marble'])
    create_wall("TF_Wall_W", Vector((0, 0, 2*FLOOR_HEIGHT)), Vector((0, DEPTH, 2*FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, tf_col).data.materials.append(mats['Sandstone'])
    create_wall("TF_Wall_N", Vector((0, DEPTH, 2*FLOOR_HEIGHT)), Vector((WIDTH, DEPTH, 2*FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, tf_col).data.materials.append(mats['Sandstone'])
    create_wall("TF_Wall_S", Vector((0, 0, 2*FLOOR_HEIGHT)), Vector((WIDTH, 0, 2*FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, tf_col).data.materials.append(mats['Sandstone'])
    create_wall("TF_Wall_E", Vector((WIDTH, 0, 2*FLOOR_HEIGHT)), Vector((WIDTH, DEPTH, 2*FLOOR_HEIGHT)), FLOOR_HEIGHT, WALL_THICKNESS, tf_col).data.materials.append(mats['Sandstone'])

    add_furniture_tf(mats, tf_col)

    # Terrace
    create_floor("Terrace_Floor", 0, 0, WIDTH, DEPTH, 0.2, 3*FLOOR_HEIGHT, terr_col).data.materials.append(mats['Sandstone'])

    # Pergola on Terrace (North side)
    for i in range(10):
        beam = create_furniture_primitive(f"Pergola_Beam_{i}", (WIDTH/2, 5 + i*0.8, 3*FLOOR_HEIGHT + 2.5), (WIDTH, 0.1, 0.1), mats['Wood'], terr_col)
    create_furniture_primitive("Pergola_Post_1", (0.1, 5, 3*FLOOR_HEIGHT + 1.25), (0.15, 0.15, 2.5), mats['Wood'], terr_col)
    create_furniture_primitive("Pergola_Post_2", (WIDTH-0.1, 5, 3*FLOOR_HEIGHT + 1.25), (0.15, 0.15, 2.5), mats['Wood'], terr_col)
    create_furniture_primitive("Pergola_Post_3", (0.1, 13, 3*FLOOR_HEIGHT + 1.25), (0.15, 0.15, 2.5), mats['Wood'], terr_col)
    create_furniture_primitive("Pergola_Post_4", (WIDTH-0.1, 13, 3*FLOOR_HEIGHT + 1.25), (0.15, 0.15, 2.5), mats['Wood'], terr_col)

    # Plants (Green blocks for now)
    create_furniture_primitive("Tulsi_Plant", (WIDTH-2, DEPTH-2, 3*FLOOR_HEIGHT + 0.4), (0.4, 0.4, 0.8), mats['Green'], terr_col)

    # Roof Overhang
    roof_overhang = create_floor("Roof_Overhang", -0.5, -0.5, WIDTH+1, DEPTH+1, 0.1, 4*FLOOR_HEIGHT, terr_col)
    roof_overhang.data.materials.append(mats['Sandstone'])

    # Setup Light/Cam/Render
    setup_lighting()
    setup_cameras()
    setup_render_settings()

if __name__ == "__main__":
    # Clear existing mesh objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Run generator
    generate_full_house()

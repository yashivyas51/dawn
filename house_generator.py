import bpy
import bmesh
import math
from mathutils import Vector, Color

# ==========================================================
# 1. PRODUCTION-LEVEL CONFIGURATION (Ahmedabad, Gujarat)
# ==========================================================
# Site: 85 sq yard plot (~18ft x 42ft)
FT_TO_M = 0.3048
DEPTH_EW = 42 * FT_TO_M  # ~12.8m (Front to Back)
WIDTH_NS = 18 * FT_TO_M  # ~5.48m (Frontage)
FLOOR_H = 3.2            # ~10.5ft Floor to Floor
WALL_THK = 0.23          # 9 inch main wall
INT_THK = 0.115          # 4.5 inch partition
WIN_H = 1.2
DOOR_H = 2.1

# Orientation: X+ is East (Entrance), Y+ is North, Z+ is Up
# Vastu: Entrance East, Kitchen SE, Pooja NE, Master SW, Stairs SW/West

# ==========================================================
# 2. CORE UTILITIES
# ==========================================================
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for mat in bpy.data.materials: bpy.data.materials.remove(mat)
    for col in bpy.data.collections:
        if col.name != "Scene Collection": bpy.data.collections.remove(col)
    for cam in bpy.data.cameras: bpy.data.cameras.remove(cam)
    for lgt in bpy.data.lights: bpy.data.lights.remove(lgt)
    for cur in bpy.data.curves: bpy.data.curves.remove(cur)

def create_col(name, parent=None):
    c = bpy.data.collections.new(name)
    if parent: parent.children.link(c)
    else: bpy.context.scene.collection.children.link(c)
    return c

def add_block(name, loc, scale, mat, col, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale; o.rotation_euler = rot
    if mat: o.data.materials.append(mat)
    # Bevel for realism
    mod = o.modifiers.new(name="B", type='BEVEL'); mod.width = 0.01; mod.segments = 3
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o)
    return o

def add_wall(name, start, end, height, thk, mat, col):
    mid = (start + end) / 2; d = end - start; length = d.length; ang = math.atan2(d.y, d.x)
    return add_block(name, (mid.x, mid.y, mid.z + height/2), (length, thk, height), mat, col, (0,0,ang))

def add_opening(wall, loc, size, mats, col, door=False):
    # Boolean cutter for architectural openings
    cut = add_block("Cutter", loc, size, None, col); cut.display_type = 'WIRE'; cut.hide_render = True
    m = wall.modifiers.new(name="C", type='BOOLEAN'); m.object = cut; m.operation = 'DIFFERENCE'
    # Architectural Frame
    frm = add_block("Frame", loc, (size.x+0.05, size.y+0.05, size.z+0.05), mats['wood'], col)
    f_mod = frm.modifiers.new(name="C", type='BOOLEAN'); f_mod.object = cut; f_mod.operation = 'DIFFERENCE'
    if not door:
        add_block("Glass", loc, (size.x-0.01, 0.02, size.z-0.01), mats['glass'], col)
    return cut

# ==========================================================
# 3. ADVANCED PBR MATERIALS (Blender 4.2+ Cycles)
# ==========================================================
def setup_mats():
    mats = {}
    def pbr(name, col, r=0.5, m=0.0, t=0.0, e=0, tex=None):
        mat = bpy.data.materials.new(name=name); mat.use_nodes = True
        nodes = mat.node_tree.nodes; nodes.clear(); out = nodes.new('ShaderNodeOutputMaterial')
        bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.inputs['Base Color'].default_value = col
        bsdf.inputs['Roughness'].default_value = r; bsdf.inputs['Metallic'].default_value = m
        if tex == 'SAND':
            b = nodes.new('ShaderNodeTexBrick'); b.inputs['Scale'].default_value = 15
            b.inputs['Color1'].default_value = col; b.inputs['Color2'].default_value = (col[0]*0.9, col[1]*0.9, col[2]*0.9, 1)
            mat.node_tree.links.new(b.outputs['Color'], bsdf.inputs['Base Color'])
        if tex == 'MARBLE':
            n = nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 5; n.inputs['Detail'].default_value = 15
            mix = nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs[6].default_value = col
            mix.inputs[7].default_value = (0.7, 0.7, 0.8, 1.0)
            mat.node_tree.links.new(n.outputs['Fac'], mix.inputs[0])
            mat.node_tree.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
        if t > 0: bsdf.inputs['Transmission Weight'].default_value = t; bsdf.inputs['IOR'].default_value = 1.45
        if e > 0: bsdf.inputs['Emission Strength'].default_value = e; bsdf.inputs['Emission Color'].default_value = col
        mat.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        return mat
    mats['sand'] = pbr("Sandstone", (0.85, 0.75, 0.6, 1), 0.9, tex='SAND')
    mats['marble'] = pbr("Marble", (0.98, 0.98, 0.98, 1), 0.05, tex='MARBLE')
    mats['wood'] = pbr("TeakWood", (0.35, 0.18, 0.08, 1), 0.4)
    mats['glass'] = pbr("Glass", (1, 1, 1, 1), 0, 0, 1.0)
    mats['metal'] = pbr("Metal", (0.8, 0.8, 0.8, 1), 0.1, 1.0)
    mats['rubber'] = pbr("Rubber", (0.05, 0.05, 0.05, 1), 0.9)
    mats['fabric'] = pbr("Fabric", (0.6, 0.6, 0.6, 1), 0.9)
    mats['rgb'] = pbr("Neon", (0, 1, 1, 1), 0, 0, 0, 15)
    mats['led'] = pbr("LED_Warm", (1, 0.9, 0.7, 1), 0, 0, 0, 10)
    mats['green'] = pbr("Green", (0.1, 0.4, 0.1, 1), 0.8)
    return mats

# ==========================================================
# 4. DETAILED FURNITURE BUILDERS
# ==========================================================
def add_detailed_sofa(loc, rot, mats, col):
    add_block("S_Base", loc, (2.2, 0.9, 0.4), mats['fabric'], col, (0,0,rot))
    add_block("S_Back", (loc[0]+(0.35*math.sin(rot)), loc[1]+(0.35*math.cos(rot)), loc[2]+0.4), (2.2, 0.15, 0.7), mats['fabric'], col, (0,0,rot))
def add_detailed_bed(loc, rot, mats, col):
    add_block("B_Frame", loc, (2.1, 1.9, 0.4), mats['wood'], col, (0,0,rot))
    add_block("B_Mat", (loc[0], loc[1], loc[2]+0.2), (2, 1.8, 0.35), mats['fabric'], col, (0,0,rot))
def add_table(loc, size, mats, col):
    add_block("T_Top", loc, size, mats['wood'], col)
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            add_block("T_Leg", (loc[0]+sx*(size.x/2-0.1), loc[1]+sy*(size.y/2-0.1), loc[2]-size.z/2-0.35), (0.1, 0.1, 0.7), mats['metal'], col)

# ==========================================================
# 5. FULL 3-STOREY ARCHITECTURAL GENERATOR
# ==========================================================
def generate():
    clear_scene(); mats = setup_mats(); root = create_col("Ahmedabad_Production_House")

    # 0. EXTERIOR
    env = create_col("00_Exterior", root)
    add_block("Ground", (DEPTH_EW/2, WIDTH_NS/2, -0.05), (100, 100, 0.01), mats['sand'], env)

    # 1. GROUND FLOOR (GF)
    gf = create_col("01_GF", root)
    add_block("GF_Floor", (DEPTH_EW/2, WIDTH_NS/2, -0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['marble'], gf)
    # Outer Walls
    we_gf = add_wall("GF_E", Vector((DEPTH_EW,0,0)), Vector((DEPTH_EW,WIDTH_NS,0)), FLOOR_H, WALL_THK, mats['sand'], gf)
    ww_gf = add_wall("GF_W", Vector((0,0,0)), Vector((0,WIDTH_NS,0)), FLOOR_H, WALL_THK, mats['sand'], gf)
    ws_gf = add_wall("GF_S", Vector((0,0,0)), Vector((DEPTH_EW,0,0)), FLOOR_H, WALL_THK, mats['sand'], gf)
    wn_gf = add_wall("GF_N", Vector((0,WIDTH_NS,0)), Vector((DEPTH_EW,WIDTH_NS,0)), FLOOR_H, WALL_THK, mats['sand'], gf)

    # Vastu Placement
    add_opening(we_gf, (DEPTH_EW, WIDTH_NS-2.5, DOOR_H/2), (0.5, 1.4, DOOR_H), mats, gf, True)
    add_block("Traditional_Otla", (DEPTH_EW+1, WIDTH_NS-2.5, 0.15), (2, 5, 0.4), mats['sand'], gf)

    # GF Rooms
    add_block("NE_Pooja", (DEPTH_EW-1, WIDTH_NS-1, 0.8), (1.2, 1.2, 1.6), mats['marble'], gf)
    add_block("Kitchen_SE", (DEPTH_EW-1.5, 2, 0.45), (1.5, 3.5, 0.9), mats['marble'], gf)
    add_table((DEPTH_EW-4.5, 2, 0.75), (1.2, 1.2, 0.05), mats, gf) # Dining
    add_detailed_bed((2.5, 3, 0.2), 0, mats, gf) # SW Bed
    add_detailed_sofa((DEPTH_EW-3, WIDTH_NS/2, 0.4), math.radians(90), mats, gf) # Living
    add_block("TV_Wall", (DEPTH_EW-WALL_THK, WIDTH_NS/2, 1.5), (0.1, 3, 2), mats['wood'], gf)
    for i in range(16): add_block(f"Step_{i}", (1+i*0.3, 0.9, i*0.2), (0.35, 1.8, 0.2), mats['marble'], gf) # SW Stairs
    add_block("GF_Toilet", (2, WIDTH_NS-1.5, FLOOR_H/2), (2, 2, FLOOR_H), mats['sand'], gf) # West Bath

    # 2. FIRST FLOOR (FF)
    ff = create_col("02_FF", root); z = FLOOR_H
    add_block("FF_Floor", (DEPTH_EW/2, WIDTH_NS/2, z-0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['marble'], ff)
    for d in [(DEPTH_EW,0,z,DEPTH_EW,WIDTH_NS,z),(0,0,z,0,WIDTH_NS,z),(0,0,z,DEPTH_EW,0,z),(0,WIDTH_NS,z,DEPTH_EW,WIDTH_NS,z)]:
        add_wall("FF_Ext", Vector(d[:3]), Vector(d[3:]), FLOOR_H, WALL_THK, mats['sand'], ff)
    add_detailed_bed((2.5, 3.5, z+0.2), 0, mats, ff) # Master Bed SW
    add_detailed_bed((2.5, WIDTH_NS-3.5, z+0.2), 0, mats, ff) # 2nd Bed NW
    add_detailed_sofa((DEPTH_EW-3, WIDTH_NS/2, z+0.4), math.radians(90), mats, ff) # Family Lounge
    # Balcony East
    add_block("Balcony_Slab", (DEPTH_EW+1.2, WIDTH_NS/2, z), (2.4, WIDTH_NS, 0.2), mats['marble'], ff)
    add_block("Rail", (DEPTH_EW+2.4, WIDTH_NS/2, z+0.5), (0.05, WIDTH_NS, 1.1), mats['glass'], ff)

    # 3. THIRD FLOOR (TF) - LUXURY FOCUS
    tf = create_col("03_TF", root); z = 2 * FLOOR_H
    add_block("TF_Floor", (DEPTH_EW/2, WIDTH_NS/2, z-0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['marble'], tf)
    for d in [(DEPTH_EW,0,z,DEPTH_EW,WIDTH_NS,z),(0,0,z,0,WIDTH_NS,z),(0,0,z,DEPTH_EW,0,z),(0,WIDTH_NS,z,DEPTH_EW,WIDTH_NS,z)]:
        add_wall("TF_Ext", Vector(d[:3]), Vector(d[3:]), FLOOR_H, WALL_THK, mats['sand'], tf)
    # Main Luxury Room
    add_detailed_bed((DEPTH_EW/2, WIDTH_NS-4, z+0.2), 0, mats, tf)
    add_block("Gaming_Desk", (DEPTH_EW-1.5, WIDTH_NS-4, z+0.4), (1, 2, 0.75), mats['wood'], tf)
    add_block("Monitor", (DEPTH_EW-1.9, WIDTH_NS-4, z+1), (0.05, 1, 0.6), mats['rgb'], tf)
    # Gym
    add_block("Gym_Floor", (DEPTH_EW/4, WIDTH_NS/4, z), (DEPTH_EW/2, WIDTH_NS/2, 0.05), mats['rubber'], tf)
    add_block("Gym_Bench", (DEPTH_EW/4, WIDTH_NS/4, z+0.25), (1.6, 0.6, 0.5), mats['metal'], tf)
    add_block("Gym_Mirror", (0.1, WIDTH_NS/4, z+1.5), (0.02, 3, 2.5), mats['glass'], tf)
    # Changing & Bath
    add_block("TF_Wardrobe", (2, WIDTH_NS-1, z+1.5), (3, 0.8, 3), mats['wood'], tf)
    add_block("TF_Shower", (2, WIDTH_NS-4, z+1.5), (2, 2, 3), mats['glass'], tf)

    # 4. TERRACE
    tr = create_col("04_Terrace", root); z = 3 * FLOOR_H
    add_block("TR_Floor", (DEPTH_EW/2, WIDTH_NS/2, z-0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['sand'], tr)
    for i in range(15): add_block(f"P_Beam_{i}", (DEPTH_EW-6, 1+i*0.8, z+2.8), (8, 0.15, 0.15), mats['wood'], tr) # Pergola
    add_block("Tulsi_Shrine", (DEPTH_EW-1.5, WIDTH_NS-1.5, z+0.4), (0.8, 0.8, 0.9), mats['marble'], tr)
    add_block("Plant", (DEPTH_EW-1.5, WIDTH_NS-1.5, z+1.2), (0.5, 0.5, 1.2), mats['green'], tr)
    for x in range(3): add_block(f"Solar_{x}", (5+x*2, 2, z+0.1), (1.5, 2, 0.05), mats['metal'], tr, (math.radians(15), 0, 0))

    # ==========================================================
    # 6. LIGHTING, CAMERAS & RENDER SETUP
    # ==========================================================
    bpy.context.scene.world.use_nodes = True; nt = bpy.context.scene.world.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'NISHITA'; sky.sun_elevation = math.radians(15)
    nt.links.new(sky.outputs['Color'], nt.nodes.get('World Output').inputs['Surface'])
    # Interior Lights
    for f in range(3): add_block(f"L_{f}", (DEPTH_EW/2, WIDTH_NS/2, (f+1)*FLOOR_H-0.05), (DEPTH_EW-1, WIDTH_NS-1, 0.02), mats['led'], root)

    def cam(name, loc, rot, ortho=False, scale=35):
        bpy.ops.object.camera_add(location=loc, rotation=rot)
        c = bpy.context.active_object; c.name = name
        if ortho: c.data.type = 'ORTHO'; c.data.ortho_scale = scale
        return c
    cam("Cam_Isometric", (35, -25, 25), (math.radians(55), 0, math.radians(45)), True, 45)
    cam("Cam_Elevation", (DEPTH_EW+20, WIDTH_NS/2, 6), (math.radians(90), 0, math.radians(90)))
    cam("Cam_Plan", (DEPTH_EW/2, WIDTH_NS/2, 40), (0,0,0), True, 30)
    cam("Cam_Interior", (DEPTH_EW-4, WIDTH_NS/2, 1.6), (math.radians(85), 0, math.radians(-90)))

    # Walkthrough Animation
    bpy.ops.curve.primitive_bezier_circle_add(radius=25, location=(DEPTH_EW/2, WIDTH_NS/2, 7))
    path = bpy.context.active_object; path.name = "Walk_Path"
    cw = cam("Cam_Walkthrough", (0,0,0), (0,0,0))
    con = cw.constraints.new('FOLLOW_PATH'); con.target = path; con.use_fixed_location = True
    con.keyframe_insert(data_path="offset_factor", frame=1); con.offset_factor = 1; con.keyframe_insert(data_path="offset_factor", frame=250)

    # RENDER CONFIG (8K Cycles GPU)
    s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.samples = 2048; s.cycles.use_denoising = True
    s.render.resolution_x = 7680; s.render.resolution_y = 4320
    try:
        p = bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type = 'OPTIX'
        for d in p.get_devices_for_type('OPTIX'): d.use = True
    except: pass

if __name__ == "__main__":
    generate()

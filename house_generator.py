import bpy
import math
from mathutils import Vector

# ==========================================================
# 1. ARCHITECTURAL CONFIGURATION (AHMEDABAD VASTU)
# ==========================================================
# Site: 85 sq yard plot (~18ft x 42ft)
FT_TO_M = 0.3048
DEPTH_EW = 42 * FT_TO_M  # ~12.80m (East-West Depth)
WIDTH_NS = 18 * FT_TO_M  # ~5.48m (North-South Frontage)
FLOOR_H = 3.2            # ~10.5 ft Floor to Floor
WALL_THK = 0.23          # 9 inch main wall
INT_THK = 0.115          # 4.5 inch partition
WIN_H = 1.3
DOOR_H = 2.1

# Orientation Logic:
# X-axis: Back (West) to Front (East). X=DEPTH_EW is East Entrance.
# Y-axis: South to North. Y=0 is South, Y=WIDTH_NS is North.
# Z-axis: Vertical.

# ==========================================================
# 2. CORE SYSTEM UTILITIES
# ==========================================================
def cleanup():
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for m in bpy.data.materials: bpy.data.materials.remove(m)
    for c in bpy.data.collections:
        if c.name != "Scene Collection": bpy.data.collections.remove(c)
    for l in bpy.data.lights: bpy.data.lights.remove(l)
    for cam in bpy.data.cameras: bpy.data.cameras.remove(cam)
    for cur in bpy.data.curves: bpy.data.curves.remove(cur)

def create_col(name, parent=None):
    c = bpy.data.collections.new(name)
    if parent: parent.children.link(c)
    else: bpy.context.scene.collection.children.link(c)
    return c

def add_block(name, loc, size, mat, col, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = size; o.rotation_euler = rot
    if mat: o.data.materials.append(mat)
    # Realistic detail: Bevel
    bvl = o.modifiers.new(name="B", type='BEVEL'); bvl.width = 0.01; bvl.segments = 3
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o)
    return o

def add_cyl(name, loc, radius, depth, mat, col, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    if mat: o.data.materials.append(mat)
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o)
    return o

def add_wall(name, p1, p2, h, thk, mat, col):
    mid = (p1 + p2) / 2; diff = p2 - p1; length = diff.length; ang = math.atan2(diff.y, diff.x)
    return add_block(name, (mid.x, mid.y, mid.z + h/2), (length, thk, h), mat, col, (0,0,ang))

def add_hole(wall, loc, size, mats, col, door=False):
    # Architectural Opening Logic
    cut = add_block("Cutter", loc, size, None, col); cut.display_type = 'WIRE'; cut.hide_render = True
    m = wall.modifiers.new(name="C", type='BOOLEAN'); m.object = cut; m.operation = 'DIFFERENCE'
    # Frame
    f = add_block("Frame", loc, (size.x+0.06, size.y+0.06, size.z+0.06), mats['wood'], col)
    fm = f.modifiers.new(name="C", type='BOOLEAN'); fm.object = cut; fm.operation = 'DIFFERENCE'
    if not door:
        add_block("Glass", loc, (size.x-0.02, 0.02, size.z-0.02), mats['glass'], col)
        # Mullions
        add_block("Mullion_V", loc, (0.04, 0.03, size.z), mats['metal'], col)
        add_block("Mullion_H", loc, (size.x, 0.03, 0.04), mats['metal'], col)
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
            b = nodes.new('ShaderNodeTexBrick'); b.inputs['Scale'].default_value = 16
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
    mats['sand'] = pbr("Ahmedabad_Sandstone", (0.85, 0.75, 0.6, 1), 0.9, tex='SAND')
    mats['marble'] = pbr("Polished_Marble", (0.98, 0.98, 0.98, 1), 0.05, tex='MARBLE')
    mats['wood'] = pbr("Dark_Teak", (0.35, 0.18, 0.08, 1), 0.45)
    mats['glass'] = pbr("Clear_Glass", (1, 1, 1, 1), 0, 0, 1.0)
    mats['metal'] = pbr("Brushed_Steel", (0.8, 0.8, 0.8, 1), 0.1, 1.0)
    mats['fabric'] = pbr("Luxury_Fabric", (0.55, 0.55, 0.6, 1), 0.9)
    mats['rgb'] = pbr("Cyber_Neon", (0, 1, 1, 1), 0, 0, 0, 15)
    mats['led'] = pbr("Warm_LED", (1, 0.95, 0.8, 1), 0, 0, 0, 10)
    mats['rubber'] = pbr("Gym_Rubber", (0.04, 0.04, 0.04, 1), 0.9)
    mats['green'] = pbr("Plant_Green", (0.1, 0.4, 0.1, 1), 0.8)
    return mats

# ==========================================================
# 4. DETAILED FURNITURE BUILDERS
# ==========================================================
def add_detailed_sofa(loc, rot, mats, col):
    add_block("S_Base", loc, (2.2, 0.9, 0.4), mats['fabric'], col, (0,0,rot))
    add_block("S_Back", (loc[0]+(0.35*math.sin(rot)), loc[1]+(0.35*math.cos(rot)), loc[2]+0.4), (2.2, 0.2, 0.8), mats['fabric'], col, (0,0,rot))
    add_block("S_Leg1", (loc[0]-1, loc[1]-0.4, loc[2]-0.25), (0.1, 0.1, 0.2), mats['metal'], col, (0,0,rot))
    add_block("S_Leg2", (loc[0]+1, loc[1]-0.4, loc[2]-0.25), (0.1, 0.1, 0.2), mats['metal'], col, (0,0,rot))

def add_detailed_bed(loc, rot, mats, col):
    add_block("B_Frame", loc, (2.1, 1.9, 0.4), mats['wood'], col, (0,0,rot))
    add_block("B_Mat", (loc[0], loc[1], loc[2]+0.25), (2, 1.8, 0.35), mats['fabric'], col, (0,0,rot))
    add_block("Headboard", (loc[0], loc[1]-1, loc[2]+0.6), (2.1, 0.15, 1.2), mats['fabric'], col, (0,0,rot))

def add_kitchen_full(loc, mats, col):
    add_block("Counter", loc, (1.2, 4, 0.9), mats['marble'], col)
    add_block("Cab_B", (loc[0], loc[1], loc[2]-0.4), (1.1, 4, 0.85), mats['wood'], col)
    add_block("Cab_T", (loc[0], loc[1], loc[2]+1.6), (0.8, 4, 0.9), mats['wood'], col)
    add_block("Fridge", (loc[0], loc[1]-2.5, loc[2]+0.5), (0.9, 0.9, 2.0), mats['metal'], col)

def add_table(loc, size, mats, col):
    add_block("T_Top", loc, size, mats['wood'], col)
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            add_block("T_Leg", (loc[0]+sx*(size.x/2-0.1), loc[1]+sy*(size.y/2-0.1), loc[2]-0.4), (0.1, 0.1, 0.8), mats['metal'], col)

# ==========================================================
# 5. CORE ARCHITECTURE (3 STOREYS + TERRACE)
# ==========================================================
def generate_ultimate_house():
    cleanup(); mats = setup_mats(); root = create_col("Ahmedabad_Luxury_Villa")

    # 0. EXTERIOR
    env = create_col("00_Exterior", root)
    add_block("Ground_Plane", (DEPTH_EW/2, WIDTH_NS/2, -0.05), (100, 100, 0.01), mats['sand'], env)

    # 1. GROUND FLOOR (GF)
    gf = create_col("01_GF", root)
    add_block("GF_Floor_Slab", (DEPTH_EW/2, WIDTH_NS/2, -0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['marble'], gf)
    we_gf = add_wall("GF_Wall_E", Vector((DEPTH_EW,0,0)), Vector((DEPTH_EW,WIDTH_NS,0)), FLOOR_H, WALL_THK, mats['sand'], gf)
    ww_gf = add_wall("GF_Wall_W", Vector((0,0,0)), Vector((0,WIDTH_NS,0)), FLOOR_H, WALL_THK, mats['sand'], gf)
    ws_gf = add_wall("GF_Wall_S", Vector((0,0,0)), Vector((DEPTH_EW,0,0)), FLOOR_H, WALL_THK, mats['sand'], gf)
    wn_gf = add_wall("GF_Wall_N", Vector((0,WIDTH_NS,0)), Vector((DEPTH_EW,WIDTH_NS,0)), FLOOR_H, WALL_THK, mats['sand'], gf)

    # Entrance & Otla
    add_opening(we_gf, (DEPTH_EW, WIDTH_NS-2.5, DOOR_H/2), (0.5, 1.4, DOOR_H), mats, gf, True) # East Entrance
    add_block("Traditional_Otla", (DEPTH_EW+1.2, WIDTH_NS-2.5, 0.15), (2.4, 5.0, 0.4), mats['sand'], gf)

    # GF Rooms
    add_block("NE_Pooja", (DEPTH_EW-1.0, WIDTH_NS-1.0, 0.8), (1.2, 1.2, 1.6), mats['marble'], gf)
    add_kitchen_full((DEPTH_EW-1.2, 3.5, 0.45), mats, gf) # SE Kitchen
    add_table((DEPTH_EW-4.5, 3.5, 0.75), (1.2, 1.2, 0.05), mats, gf) # 4-Seater Dining
    add_detailed_bed((2.5, 3.5, 0.2), 0, mats, gf) # SW Guest Bedroom
    add_detailed_sofa((DEPTH_EW-3.5, WIDTH_NS/2, 0.4), math.radians(90), mats, gf) # Living
    for i in range(16): add_block(f"Step_{i}", (1.2+i*0.32, 1.0, i*0.2), (0.35, 1.8, 0.2), mats['marble'], gf) # SW Stairs

    # 2. FIRST FLOOR (FF)
    ff = create_col("02_FF", root); z = FLOOR_H
    add_block("FF_Floor_Slab", (DEPTH_EW/2, WIDTH_NS/2, z-0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['marble'], ff)
    for d in [(DEPTH_EW,0,z,DEPTH_EW,WIDTH_NS,z),(0,0,z,0,WIDTH_NS,z),(0,0,z,DEPTH_EW,0,z),(0,WIDTH_NS,z,DEPTH_EW,WIDTH_NS,z)]:
        add_wall("FF_Ext", Vector(d[:3]), Vector(d[3:]), FLOOR_H, WALL_THK, mats['sand'], ff)
    # Master Bedroom (SW)
    add_detailed_bed((2.8, 4, z+0.2), 0, mats, ff)
    add_block("FF_Master_Wardrobe", (1, 8, z+1.5), (1, 4, 3.0), mats['wood'], ff)
    # Balcony & Lounge
    add_detailed_sofa((DEPTH_EW-3, WIDTH_NS/2, z+0.4), math.radians(90), mats, ff)
    add_block("FF_Balcony_Slab", (DEPTH_EW+1.2, WIDTH_NS/2, z), (2.4, WIDTH_NS, 0.2), mats['marble'], ff)
    add_block("FF_Balcony_Rail", (DEPTH_EW+2.35, WIDTH_NS/2, z+0.55), (0.05, WIDTH_NS, 1.1), mats['glass'], ff)

    # 3. THIRD FLOOR (TF) - LUXURY FOCUS
    tf = create_col("03_TF", root); z = 2 * FLOOR_H
    add_block("TF_Floor_Slab", (DEPTH_EW/2, WIDTH_NS/2, z-0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['marble'], tf)
    for d in [(DEPTH_EW,0,z,DEPTH_EW,WIDTH_NS,z),(0,0,z,0,WIDTH_NS,z),(0,0,z,DEPTH_EW,0,z),(0,WIDTH_NS,z,DEPTH_EW,WIDTH_NS,z)]:
        add_wall("TF_Ext", Vector(d[:3]), Vector(d[3:]), FLOOR_H, WALL_THK, mats['sand'], tf)
    # Luxury Room & Workstation
    add_detailed_bed((DEPTH_EW/2, WIDTH_NS-4, z+0.2), 0, mats, tf)
    add_block("Gaming_Desk", (DEPTH_EW-1.5, WIDTH_NS-4, z+0.4), (1.2, 2.5, 0.8), mats['wood'], tf)
    add_block("Neon_Monitor", (DEPTH_EW-2.0, WIDTH_NS-4, z+1.0), (0.05, 1.2, 0.6), mats['rgb'], tf)
    # Gym Area
    add_block("Gym_Flooring", (DEPTH_EW/4, WIDTH_NS/4, z), (DEPTH_EW/2, WIDTH_NS/2, 0.05), mats['rubber'], tf)
    add_block("Gym_Bench", (DEPTH_EW/4, WIDTH_NS/4, z+0.25), (1.6, 0.6, 0.5), mats['metal'], tf)
    add_cyl("Dumbbell_1", (DEPTH_EW/4+1, WIDTH_NS/4+0.5, z+0.2), 0.1, 0.4, mats['metal'], tf, (0, math.radians(90), 0))
    add_cyl("Dumbbell_2", (DEPTH_EW/4+1, WIDTH_NS/4-0.5, z+0.2), 0.1, 0.4, mats['metal'], tf, (0, math.radians(90), 0))

    # 4. TERRACE
    tr = create_col("04_Terrace", root); z = 3 * FLOOR_H
    add_block("TR_Floor_Slab", (DEPTH_EW/2, WIDTH_NS/2, z-0.1), (DEPTH_EW, WIDTH_NS, 0.2), mats['sand'], tr)
    # Pergola
    for i in range(15): add_block(f"P_Beam_{i}", (DEPTH_EW-6, 1.5+i*0.9, z+2.9), (8, 0.15, 0.15), mats['wood'], tr)
    # Plants & Solar
    add_block("Tulsi_Shrine", (DEPTH_EW-1.5, WIDTH_NS-1.5, z+0.45), (0.8, 0.8, 0.9), mats['marble'], tr)
    add_block("Tulsi_Plant", (DEPTH_EW-1.5, WIDTH_NS-1.5, z+1.1), (0.4, 0.4, 1.2), mats['green'], tr)
    for x in range(4): add_block(f"Solar_P_{x}", (4+x*2, 2.5, z+0.1), (1.6, 2.2, 0.05), mats['metal'], tr, (math.radians(15), 0, 0))

    # ==========================================================
    # 6. LIGHTING, CAMERAS & RENDER SETUP
    # ==========================================================
    # Nishita Sky Golden Hour
    bpy.context.scene.world.use_nodes = True; nt = bpy.context.scene.world.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'NISHITA'; sky.sun_elevation = math.radians(15)
    nt.links.new(sky.outputs['Color'], nt.nodes.get('World Output').inputs['Surface'])
    # Ceiling LEDs
    for f in range(3): add_block(f"L_Strip_{f}", (DEPTH_EW/2, WIDTH_NS/2, (f+1)*FLOOR_H-0.05), (DEPTH_EW-1, WIDTH_NS-1, 0.02), mats['led'], root)

    def setup_cam(name, loc, rot, ortho=False, scale=35):
        bpy.ops.object.camera_add(location=loc, rotation=rot)
        c = bpy.context.active_object; c.name = name
        if ortho: c.data.type = 'ORTHO'; c.data.ortho_scale = scale
        return c
    setup_cam("Cam_Isometric", (38, -28, 28), (math.radians(55), 0, math.radians(50)), True, 45)
    setup_cam("Cam_Front_Elevation", (DEPTH_EW+22, WIDTH_NS/2, 7), (math.radians(90), 0, math.radians(90)))
    setup_cam("Cam_Top_Plan", (DEPTH_EW/2, WIDTH_NS/2, 45), (0,0,0), True, 30)

    # Walkthrough Animation
    bpy.ops.curve.primitive_bezier_circle_add(radius=25, location=(DEPTH_EW/2, WIDTH_NS/2, 7))
    path = bpy.context.active_object; path.name = "Walk_Path"
    cw = setup_cam("Cam_Walkthrough", (0,0,0), (0,0,0))
    con = cw.constraints.new('FOLLOW_PATH'); con.target = path; con.use_fixed_location = True
    con.keyframe_insert(data_path="offset_factor", frame=1); con.offset_factor = 1; con.keyframe_insert(data_path="offset_factor", frame=250)

    # PRODUCTION RENDER CONFIG (8K Cycles)
    s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.samples = 2048; s.cycles.use_denoising = True
    s.render.resolution_x = 7680; s.render.resolution_y = 4320
    try:
        p = bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type = 'OPTIX'
        for d in p.get_devices_for_type('OPTIX'): d.use = True
    except: pass

if __name__ == "__main__":
    generate_ultimate_house()

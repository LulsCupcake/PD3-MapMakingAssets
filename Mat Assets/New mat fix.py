import unreal
import json
import os

# --- CONFIG ---
base_dir = os.path.expanduser("~")
json_path = os.path.join(base_dir, "Documents", "GitHub", "PD3-Modding-Project", "Script", "ObjectInfo.json")
texture_source_folder = os.path.join(base_dir, "Documents", "GitHub", "PD3-Modding-Project", "Content")



# --- HELPERS ---

def normalize_unreal_path(raw_path):
    path = raw_path.replace(".0", "")
    if path.startswith("Game/"):
        return path.replace("Game/", "/Game/", 1)
    elif path.startswith("Engine/"):
        return path.replace("Engine/", "/Engine/", 1)
    elif path.startswith("/") and ("/Game/" in path or "/Engine/" in path):
        return path
    else:
        return None

def guess_param_name(tex_name):
    name = tex_name.upper()
    if "BR" in name:
        return "BaseTexture"
    elif "NMA" in name or "NM" in name:
        return "NormalMap"
    elif "ORM" in name:
        return "ORM"
    return "Texture"

def import_texture(texture_file_path, destination_path, destination_name):
    task = unreal.AssetImportTask()
    task.set_editor_property('automated', True)
    task.set_editor_property('destination_path', destination_path)
    task.set_editor_property('destination_name', destination_name)
    task.set_editor_property('filename', texture_file_path)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    task.set_editor_property('factory', unreal.TextureFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return f"{destination_path}/{destination_name}"

def create_basic_master_material(master_path):
    if unreal.EditorAssetLibrary.does_asset_exist(master_path):
        return unreal.load_asset(master_path)

    name = os.path.basename(master_path)
    folder = os.path.dirname(master_path)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.Material, unreal.MaterialFactoryNew()
    )

    editor_util = unreal.MaterialEditingLibrary

    # BaseColor
    tex_base = editor_util.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -384, 0)
    tex_base.set_editor_property("parameter_name", "BaseTexture")
    editor_util.connect_material_property(tex_base, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)

    # Normal
    tex_norm = editor_util.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -384, 200)
    tex_norm.set_editor_property("parameter_name", "NormalMap")
    editor_util.connect_material_property(tex_norm, "RGB", unreal.MaterialProperty.MP_NORMAL)

    # ORM
    tex_orm = editor_util.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -384, 400)
    tex_orm.set_editor_property("parameter_name", "ORM")
    editor_util.connect_material_property(tex_orm, "RGB", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)

    unreal.EditorAssetLibrary.save_asset(master_path)
    return material

# --- MAIN ---

with open(json_path, "r") as f:
    object_data = json.load(f)

all_materials = set()

# Gather all unique material interface paths
for obj in object_data:
    for mat in obj.get("StaticMaterials", []):
        path = normalize_unreal_path(mat.get("MaterialInterface", {}).get("ObjectPath", ""))
        if path:
            all_materials.add(path)

print(f"\n[INFO] Found {len(all_materials)} unique material paths\n")

for mi_path in all_materials:
    if "/Engine/" in mi_path:
        print(f"[SKIP] Engine material: {mi_path}")
        continue

    mi_name = os.path.basename(mi_path)
    mi_folder = os.path.dirname(mi_path)
    mm_name = "M_" + mi_name.replace("MI_", "")
    mm_path = f"{mi_folder}/{mm_name}"

    # Create master if needed
    master = create_basic_master_material(mm_path)

    # Create material instance
    if unreal.EditorAssetLibrary.does_asset_exist(mi_path):
        print(f"[SKIP] MI exists: {mi_path}")
        continue

    mi_factory = unreal.MaterialInstanceConstantFactoryNew()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    new_mi = asset_tools.create_asset(
        mi_name, mi_folder, unreal.MaterialInstanceConstant, mi_factory
    )
    new_mi.set_editor_property("parent", master)

    # Now assign textures (if available from same folder)
    tex_base = os.path.basename(mi_path)

    # Search the original object data for matching texture info
    for obj in object_data:
        for mat in obj.get("StaticMaterials", []):
            mat_obj_path = normalize_unreal_path(mat.get("MaterialInterface", {}).get("ObjectPath", ""))
            if mat_obj_path != mi_path:
                continue

            for tex_entry in mat.get("TextureParameterValues", []):
                tex_path_raw = tex_entry.get("ObjectPath", "")
                tex_path = normalize_unreal_path(tex_path_raw)
                if not tex_path:
                    continue

                tex_name = os.path.basename(tex_path)
                param_name = guess_param_name(tex_name)
                rel_tex_path = tex_path.replace("/Game/", "")
                disk_path = os.path.join(texture_source_folder, rel_tex_path + ".png")

                if not unreal.EditorAssetLibrary.does_asset_exist(tex_path):
                    if os.path.exists(disk_path):
                        import_texture(disk_path, os.path.dirname(tex_path), tex_name)
                        print(f"  [IMPORT] {tex_name}")
                    else:
                        print(f"  [MISSING FILE] {disk_path}")
                        continue

                texture = unreal.load_asset(tex_path)
                if not texture:
                    continue

                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                    new_mi, param_name, texture
                )
                print(f"  [SET] {mi_name} → {param_name} = {texture.get_name()}")

    unreal.EditorAssetLibrary.save_asset(mi_path)
    print(f"[DONE] Created and assigned textures for MI: {mi_path}\n")

import bpy
import bmesh
import os
import struct


def save(operator, context, filename=""):
    models = {}

    for o in bpy.data.objects:
        if o.type != 'MESH':
            print("Skipped object:", o.name, "of type:", o.type)
            continue  # Skip if it's not a mesh
        print("Exporting object: " + o.name)
        models[o.name] = {}  # Each model is a dict
        model = models[o.name]
        mesh = o.data
        
        # Get texture name - Blender 4.4 uses a node-based material system
        print("Reading materials to find the texture")
        
        # Initialize texture name as None
        model['texture_name'] = None
        
        # Look through materials for texture nodes
        for mat_slot in o.material_slots:
            if mat_slot.material and mat_slot.material.use_nodes:
                # Look for texture nodes
                for node in mat_slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        model['texture_name'] = os.path.splitext(node.image.name)[0]
                        print(f"Found an image: {node.image.name}")
                        break

        # If not a single texture was found in any of the materials assigned raise exception
        if model.get('texture_name') is None:
            raise ValueError("No texture for assigned material found. ADD ONE! Object: " + o.name)

        # Debug output
        print("Texture name: " + model['texture_name'])

        # Calculate split normals
        mesh.calc_normals_split()
        
        # Validate the mesh
        mesh.update()
        mesh.validate()
        
        # Get bmesh for detailed data - ensure we're in object mode
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        bmesh_mesh = bmesh.new()
        bmesh_mesh.from_mesh(mesh)
        
        # Set name
        model['element_name'] = o.name
        model['shape_name'] = mesh.name
        
        # Set world matrix
        model['world_matrix'] = get_mat4(o.matrix_world)
        
        # Check if model is visible - in Blender 4.4, we need to check both viewport and render visibility
        model['is_visible'] = 0 if (o.hide_viewport or o.hide_render) else 1
        
        # Prepare vertex data structures
        model['vertex_data'] = {
            'position': [],
            'uv': [],
            'normals': [],
            'vertex_color': []
        }
        model['index_buffer'] = []

        # Get UV layer
        uv_layer = None
        if bmesh_mesh.loops.layers.uv:
            uv_layer = bmesh_mesh.loops.layers.uv.active
        
        # Check for vertex colors
        has_vertex_
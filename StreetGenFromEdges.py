bl_info = {
    "name": "StreetGenFromEdges",
    "author": "Felix Nickel",
    "location": "View3D > Sidebar > Gen Tab",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "description": "Generate streets from the edes of a mesh object",
    "category": "Object"
    }

import bpy
import mathutils
import bmesh
import numpy
import math

#This script is supposed to create street geometry with circular beveld corners
#The edges of a user created mesh is the base from which it creates the streets from
#Select the Mesh Object and the Generation Button should appear in the 'Sidebar>>Gen'

#***************create Panel****************
class VIEW3D_PT_Street_from_edges(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gen"
    bl_label = "Street From Edges"
    bl_options = {'DEFAULT_CLOSED'}
    bl_context = "objectmode" #only active when in Object Mode
    
    def draw(self, context):
        if len(bpy.context.selected_objects) == 0: #is any object selectd?
            self.layout.label(text='-No Mesh Object Selected-')
        elif not isinstance(bpy.context.selected_objects[-1].data, bpy.types.Mesh): #is the last selected object a Mesh Object?
            self.layout.label(text='-No MESH Object Selected-')
        else:
            self.layout.label(text='Note: the edges should be planar to the XY-plane of the object')
            self.layout.operator('object.street_gen')
#***************create Panel****************

#***************Operator***************

class OBJECT_OT_Street_from_edges(bpy.types.Operator):
    """Generate street from edges"""    
    bl_idname = "object.street_gen"
    bl_label = "generate street from edges"
    bl_options = {'REGISTER', 'UNDO'} #UNDO makes the panel appear in the lower feft to edit the values in 'realtime'
    
#------ set min max ------
    def SetSubdivMax ( self, context ):
        if self.SubdivMin > self.SubdivMax:
            self.SubdivMin = self.SubdivMax
        
    def SetSubdivMin ( self, context ):
        if self.SubdivMin > self.SubdivMax:
            self.SubdivMax = self.SubdivMin
    
    def SetSubdivLongLen ( self, context ):
        if self.SubdivShortLen > self.SubdivLongLen:
            self.SubdivShortLen = self.SubdivLongLen
        
    def SetSubdivShortLen ( self, context ):
        if self.SubdivShortLen > self.SubdivLongLen:
            self.SubdivLongLen = self.SubdivShortLen
    
#------ set min max ------    

    Width: bpy.props.FloatProperty(
        name = "Steet Width",
        description = "length crossing the street",
        default = 0.5,
        min = 0,
    )
    
    BevelSize: bpy.props.FloatProperty(
        name = "Bevel Size",
        description = "Minimal Bevel applied to the street. In a street knot, the smallest angle has this bevel, others get calculated based on that",
        default = 0.55,
        min = 0,
    )
    
    IsEndRound: bpy.props.BoolProperty(
        name = "Beveled Dead Ends",
        description = "Adds a rounded end segemnts to dead ends of the street",
        default = True,
    )
    
    BevelSizeDeadEnd: bpy.props.FloatProperty(
        name = "Bevel Size Dead End",
        description = "Size of the arcs at dead ends of the streets",
        default = 0.1,
        min = 0,
    )
    
    BevelSubdiv: bpy.props.IntProperty(
        name = "Subdivision Count",
        description = "subdivisions of the bevel/arc (only active, when 'Angle Based' and 'Edge Length' are not in use)",
        default = 16,
        min = 0,
    )
    
    AngleThreshold: bpy.props.FloatProperty(
        name = "Subdiv Threshold Angle",
        description = "street corner angles higher than this will not be subdivided. 180° = every street coner gets subdivided",
        #subtype = 'ANGLE', #problem with the accuracy conversion to radians 
        default = 170, #default = 2.96706,
        min = 0,
        max = 180, #max = 3.14159265359,
    )
    
    IsSubdivAngBased: bpy.props.BoolProperty(
        name = "Angle Based",
        description = "Use an angle at wich subdivision of an arc starts. (lower angle = higher subdivision count. 'Edge Length' will cap the subdivision count)",
        default = True,
    )
    
    SubdivAngle: bpy.props.FloatProperty(
        name = "Min Subdiv Angle",
        description = "Angle at which subdivision of an arc starts. (lower angle = higher subdivision count. 'Edge Length' will cap the subdivision count)",
        #subtype = 'ANGLE', #problem with the accuracy conversion to radians 
        default = 11, #default = 0.2,
        min = 0,
        max = 360, #max = 6.28318530717,
    )
    
    IsSubdivLenBased: bpy.props.BoolProperty(
        name = "Edge Length Based",
        description = "Use a shortest/longest edge length for the subdivision of an arc. The longest only is in use when 'Angle Based' is active too, because then the 'Angle Based' could create more subdivisions which could be capped by the shortest edge length",
        default = True,
    )
    
    SubdivShortLen: bpy.props.FloatProperty(
        name = "Shortest Edge Length",
        description = "Shortest length of an edge in the arc. (only is in use when 'Angle Based' is active. Useful on very large arcs that would make a subdivision count by angle visually obvious)",
        default = 0.05,
        min = 0,
        update = SetSubdivShortLen
    )
    
    SubdivLongLen: bpy.props.FloatProperty(
        name = "Longest Edge Length",
        description = "Maximum length of an edge in the arc",
        default = 0.5,
        min = 0,
        update = SetSubdivLongLen
    )
    
    SubdivMin: bpy.props.IntProperty(
        name = "Subdiv Count Min",
        description = "Minimum subdivisions per arc",
        default = 0,
        min = 0,
        soft_max = 128,
        update = SetSubdivMin
    )
    
    SubdivMax: bpy.props.IntProperty(
        name = "Subdiv Count Max",
        description = "Maximum subdivisions per arc",
        default = 64,
        min = 0,
        soft_max = 128,
        update = SetSubdivMax
    )
    #***************undo panel layout - the realtime edit box down left in 3DView - search for: bl_options = 'UNDO'***************
    def draw(self, context): 
        if len(bpy.context.selected_objects) == 0: #is any object selectd?
            self.layout.label(text='-No Mesh Object Selected-')
        elif not isinstance(bpy.context.selected_objects[-1].data, bpy.types.Mesh): #is the last selected object a Mesh Object?
            self.layout.label(text='-No Mesh Object Selected-')
        else:            
            layout = self.layout

            layout.prop(self,'Width')
            layout.prop(self,'BevelSize')
            
            layout.prop(self,'IsEndRound')
            col = layout.column()
            col.active = self.IsEndRound
            col.prop(self,'BevelSizeDeadEnd')
            
            col.label(text='Subdivision Settings:')
            #----------Start: Box----------
            box = layout.box()
            col = box.column()
            col.active = not (self.IsSubdivLenBased or self.IsSubdivAngBased) #only active if both options are false
            col.prop(self, 'BevelSubdiv')
            
            box.prop(self,'AngleThreshold')
            
            box.prop(self,'IsSubdivAngBased')
            col = box.column()
            col.active = self.IsSubdivAngBased
            col.prop(self, 'SubdivAngle')
            
            box.prop(self,'IsSubdivLenBased')        
            col0 = box.column( align = True ) #level0 column, that contains the 2 columns with a property each
            col0.active = self.IsSubdivLenBased
            col = col0.column( align = True )  #align = True puts together multiple properties into one block
            col.prop(self, 'SubdivShortLen', text='') #text='' removes the visible name in the panel
            col.active = self.IsSubdivAngBased
            col = col0.column( align = True ) #align = True puts together multiple properties into one block
            col.prop(self, 'SubdivLongLen', text='') #text='' removes the visible name in the panel
        
            col0 = box.column( align = True ) #level0 column, that contains the 2 columns with a property each
            col0.active = self.IsSubdivAngBased or self.IsSubdivLenBased
            col0.label(text='Subdiv Count Min/Max')
            col = col0.column( align = True )  #align = True puts together multiple properties into one block
            col.prop(self, 'SubdivMin', text='') #text='' removes the visible name in the panel
            col = col0.column( align = True ) #align = True puts together multiple properties into one block
            test = col.prop(self, 'SubdivMax', text='') #text='' removes the visible name in the panel
            #----------End: Box----------
        
    def execute(self, context):        
        
        # get the last selected object mesh
        if len(bpy.context.selected_objects) == 0: #is any object selectd?
            return {'FINISHED'}
        
        obj = bpy.context.selected_objects[-1]
        me = obj.data  #for the active object: bpy.context.object.data
        if not isinstance(me, bpy.types.Mesh): #is the last selected object a Mesh Object?
            return {'FINISHED'}

        # Get a BMesh representation
        bm = bmesh.new()   # create an empty BMesh
        bm.from_mesh(me)   # fill it in from a Mesh
        
        if self.Width == 0:
            return {'FINISHED'} #end the process before calculating anything
        
        #############------Start: Input------#############
        StrWidth = self.Width #width of the streets
        BevelSize = self.BevelSize #The distance from the corner anlong the edges. In a street knot, it is the base for the smallest angle.
        subdiv = self.BevelSubdiv #subdivisions of the bevel/arc (IsSubdivAngBased == False)
        subdivAngle = math.radians(self.SubdivAngle) #angle (IsSubdivAngBased == True)
        MinSubdiv = self.SubdivMin #minimal subdivisions, this value is always in use
        MaxSubdiv = self.SubdivMax #maximal subdivisions, this value is always in use
        MinSubdivLen = self.SubdivShortLen #minimal length an edge should have in an corner arc, this value is always in use
        MaxSubdivLen = self.SubdivLongLen #maximal length an edge should have in an corner arc, this value is always in use
        IsSubdivAngBased = self.IsSubdivAngBased #True= Subdivision of the corners grows with the angle, False= every corner get a fixed subdivision
        IsSubdivLenBased = self.IsSubdivLenBased #True = Subdivision of corners grows with ther size
        IsEndRound = self.IsEndRound #True = dead ends get rounded corners instead of a 90° cut
        BevelSizeDeadEnd = self.BevelSizeDeadEnd #bevel size of the dead end corners, if it is >= StrWidth it will be a half circle 
        rad_thr = math.radians(self.AngleThreshold) #the maximum angle to create an arc bevel on. Is the angle bigger, just one subdivision is done

        rad_fullcircle = 2*math.pi #precalculate for CreateArc(), to save processing power
        #############------End: Input------#############
        
        #############------Start: Variable Preperation------#############
        #prepare input variables for processing
        StrWidthHalf = StrWidth/2
        rad_subdivAngle = subdivAngle #subdivAngle * (math.pi / 180) #convert degree into radiens
        SubdivLenBased = 0
        SubdivAngBased = 0

        #create variables for processing
        v_remain = [] #v_remain list of remaining vertices to test
        v_remain.extend(bm.verts) #extend copies every element of the vertex data|| v_remain = bm.verts would make a refernce to that structure || v_remain.append(bm.verts) would add the vertex list as one element of the v_remain list

        edge_list = [] #list of the existing edge network for reference
        edge_list.extend(bm.edges) #copy list elements

        #generated geometry data goes in these lists
        newVerts = [] #new vertex coordinates
        #creating the list structure for creating the connecting streets
        #look in the functions addToEdgeFace and buildEdgeConnections

        ##### only indices go in here #####
        newFaces_edge_ind = [] #faces that will be created between existing faces
        for i in range(0, len(edge_list)):
            #(BottomRight), (BottomLeft), (BottomRight), (BottomRight)
            newFaces_edge_ind.append([[],[],[],[]]) #insert list with empty elements, 4 possible vertex indices for one face
        #look in the functions addToEdgeFace and buildEdgeConnections

        ##### only indices go in here #####
        #creating the list structure for creating the streets knots with arcs in it
        newFace_vert_ind = [] #faces that will be created between existing faces
        for i in range(0, len(v_remain)):
            #adding new empty list elements in a for loop
            #newFace_vert_ind = [[]]*3 would create 3 references of one list element, meaning that appending one element would create a list with 3 times the same content
            newFace_vert_ind.append([])
        #############------End: Variable Preperation------#############
                  
        def CreateArc(vertList, radius, subdiv, rad_arc, rad_offset, IsStartVertAdded, IsEndVertAdded):
            
            if radius <= 0: #abort process when radius is 0 or smaller
                return
            
            else:
                ##############------START: calculate subdivision count------#############
                if IsSubdivAngBased == True:
                    if rad_subdivAngle == 0:
                        if MinSubdivLen == 0:
                            subdiv = MaxSubdiv
                        else:
                            C = rad_arc*radius #arc Circumference #2*pi*r for full circle
                            subdiv = math.floor(C / MinSubdivLen)-1
                    else:
                        SubdivAngBased = math.floor(rad_arc/rad_subdivAngle)-1
                        if IsSubdivLenBased == False:#only angle based
                            subdiv = SubdivAngBased
                        else:# IsSubdivLenBased == True 
                            C = rad_arc*radius #arc Circumference #2*pi*r for full circle
                            if MaxSubdivLen != 0 and MinSubdivLen != 0:
                                subdiv = numpy.clip( SubdivAngBased, math.floor(C / MaxSubdivLen), math.floor(C / MinSubdivLen)-1 )
                            elif MaxSubdivLen != 0:
                                subdiv = max(SubdivAngBased, math.floor(C / MaxSubdivLen))
                        
                    subdiv = numpy.clip(subdiv, MinSubdiv, MaxSubdiv) #min/max subdiv count for angle/length based
                else: #IsSubdivAngBased = Flase
                    if IsSubdivLenBased == True and MaxSubdivLen != 0: #only based on SubdivMinLen
                        C = rad_arc*radius #arc Circumference #2*pi*r for full circle                        
                        subdiv = math.floor(C / MaxSubdivLen)-1 #only length based
                        
                        subdiv = numpy.clip(subdiv, MinSubdiv, MaxSubdiv)
                    elif IsSubdivLenBased == True:
                        subdiv = MaxSubdiv
                    else: #no change to the subdivision count
                        pass
                ##############------END: calculate subdivision count------#############
                subdiv += 1
                if IsStartVertAdded == True:
                    start = 0
                else:
                    start = 1
                
                if IsEndVertAdded == True:
                    end = subdiv + 1
                else:
                    end = subdiv
                
                #creation of the arc coordinates
                #rad_arc, rad_offset are in radiens units
                for i in range(start,end):
                    x = radius * math.cos(((i / subdiv) * rad_arc) + rad_offset)
                    y = radius * math.sin(((i / subdiv) * rad_arc) + rad_offset)
                    z = 0.0
                    vertList.append(mathutils.Vector((x,y,z))) #mathutils.Vector() initilizes/build/construct a vector
                return

        def addToVertFace(TargetKnot_ind, AddedVert_count, ExistingVert_list, newFaces_ind_list):
            #this function adds vertices into the data structure that is used later to build the faces of street knots
            #TargetKnot_ind=the index of the source geometry vertex, AddedVert_count=count of the verts in the ExistingVert_list that need to be registerd in the newFaces_ind_list, ExistingVert_list=the list of all vertex created in this whole process, newFaces_ind_list=Face struct - a list of lists, that contains vertex indices
            if len(ExistingVert_list) >= AddedVert_count: #make sure there are enough vertices registered to get indices from
                for i in range(len(ExistingVert_list) - AddedVert_count, len(ExistingVert_list)): #i=vertex index, counting backwards the existing vert index to the last index of the existing, these should be the last added arc vertices
                    newFaces_ind_list[TargetKnot_ind].append(i)
            return

        def addToEdgeFace(edge, bev_ind, vm, isRightEdge):
            #this function adds vertices into the data structure that is used later 
            #to build the faces between the street knots
            #edge = reference from base geometry, bev_ind = index of the vertex in the new geometry, vm = Corner vertex (vertex in the middle), corner_normal = the vector the bevels were created with
            #forward direction of the base geo edge is consired to be edge[0].verts[0]->[1]
            #the vertex indices, if created with the normal = (0,0,1) would be: [0] = normal.cross(edgeDir), [1] = normal.cross(edgeDir) * -1, [2] = normal.cross(edgeDir * -1), [3] = normal.cross(edgeDir * -1) * -1
            if isRightEdge: #was the edge start vertex the same as the start vertex (vm)?
                if edge.verts[0].index == vm.index:
                    newFaces_edge_ind[edge.index][3] = bev_ind #set the new values at the edge index
                else:
                    newFaces_edge_ind[edge.index][1] = bev_ind #set the new values at the edge index
            else:
                if edge.verts[0].index == vm.index:
                    newFaces_edge_ind[edge.index][2] = bev_ind
                else:
                    newFaces_edge_ind[edge.index][0] = bev_ind
            
            return

        def createMesh(Verts,Faces):
            newMesh = bpy.data.meshes.new("Street")
            newObject = bpy.data.objects.new("Street", newMesh)
            newObject.location = bpy.context.selected_objects[-1].location #set newObject at the location of the selected object
            #bpy.context.scene.objects.link(newObject) #set newObject into the current scene
            bpy.context.collection.objects.link(newObject)
            newMesh.from_pydata(Verts,[],Faces) #inset the geometry data into the objects data (edges come with the faces, so they areempty here [])
            newMesh.update(calc_edges=True) #create the Object
            
            bpy.ops.object.select_all(action='DESELECT') #deselect all
            newObject.select_set(True) # select the new object
            bpy.context.view_layer.objects.active = newObject #set new objet as active element
            return

        def MakeNormalVector(Vec_right, Vec_left):
            normal = Vec_right.cross(Vec_left)
            normal_len = numpy.linalg.norm(normal)
            if normal_len == 0:
                normal = mathutils.Vector((0,0,1))
            else:
                normal /= numpy.linalg.norm(normal) #divide by its own length so it's a unify vector (length = 1)
            return normal

        class DotList: #this is used in the creation of a street crossing
          def __init__(self, edge_right, edge_left, vec_right, vec_left, dot, normal, IsGap):
            self.edge_left = edge_left
            self.edge_right = edge_right
            self.dot = dot #math dot product calculated from the left and right edge
            self.vec_left = vec_left
            self.vec_right = vec_right
            self.normal = normal
            self.IsGap = IsGap #is the angle >= 180° between the edges?

        def WorldAngleFromVector(InputVector):
            #!!! the input vector needs to be a unit vector - length of 1 !!!
            #returns the angle (in radiens:0-2*pi = 0°-360°) of a vector in Polar Coordinates
            #[1,0,0] would be 0°, [0,1,0] would be
            rad_angle = math.acos(numpy.clip(InputVector[0],-1, 1))
            if InputVector[1] < 0: #is the vector pointing below the x axis (lookin at the y-value)
                rad_angle = (2*math.pi)-rad_angle #360-(calulated angle)
            return rad_angle


        #############------Main Process------#############
        while len(v_remain)>0:
            vm = v_remain[0] #vm=vertex middle, the current processed vertex
            edgeConnections = len(vm.link_edges)
            
            if edgeConnections > 0: #if no connecting edges skip everything below and go to next vertex 
                
        ###### case: 1 connecting edge, dead end ######
                if edgeConnections < 2: 
                    edge = vm.link_edges[0]
                    v1 = edge.other_vert(vm) #vertex that is connected to the current processed vertex
                    vm_v1_dir = v1.co - vm.co #directional vector of the connection edge
                    vm_v1_dir /= numpy.linalg.norm(vm_v1_dir) #normalize vector (make length of 1)
                    widthVec = vm_v1_dir.cross([0,0,StrWidthHalf]) #vector local of the street width, rightVector of the connecting edge
                    #add vertices to list for later mesh creation
                    newVerts.append(widthVec+vm.co)
                    newVerts.append(-widthVec+vm.co)
                    
                    bev1_ind = len(newVerts)-1 #the index this vertex coordinates have
                    addToEdgeFace(edge, bev1_ind, vm, True) #the Bool (True/False) determins if the input is the left or right edge (determined by the cross product -> corner_normal)
                    bev2_ind = len(newVerts)-2 #the index this vertex coordinates have
                    addToEdgeFace(edge, bev2_ind, vm, False) #the Bool (True/False) determins if the input is the left or right edge (determined by the cross product -> corner_normal)
        ################################################
                    if IsEndRound == True:
                        arc_vert = []
                        widthVec_direct = widthVec/numpy.linalg.norm(widthVec)
                        rad_offset = WorldAngleFromVector(-widthVec_direct)
                        
                        if BevelSizeDeadEnd >= StrWidthHalf: #calculate one half circle for the dead end
                            CreateArc(arc_vert, StrWidthHalf, subdiv, (math.pi) ,rad_offset, False, False)
                            for newVertCoord in arc_vert: ##### adding the vertices to the vertex list #####
                                newVerts.append(newVertCoord + vm.co)
                            
                            addToVertFace(vm.index, len(arc_vert)+2, newVerts, newFace_vert_ind)
                        
                        else: #calculate 2 rounded corners
                            pos_offset = ((StrWidthHalf - BevelSizeDeadEnd) * -widthVec_direct)
                            CreateArc(arc_vert, BevelSizeDeadEnd, subdiv, (math.pi/2) ,rad_offset, False, True)
                            for newVertCoord in arc_vert:
                                ##### adding the vertices to the vertex list #####
                                newVerts.append(newVertCoord + vm.co + pos_offset)
                            
                            arc_vert = [] #clear list
                            rad_offset = WorldAngleFromVector(-vm_v1_dir) #offset should be +90° to the old rad_offset value
                            CreateArc(arc_vert, BevelSizeDeadEnd, subdiv, (math.pi/2) ,rad_offset, True, False)
                            pos_offset = -pos_offset
                            for newVertCoord in arc_vert: ##### adding the vertices to the vertex list #####
                                newVerts.append(newVertCoord + vm.co + pos_offset)
                                
                            addToVertFace(vm.index, len(arc_vert)*2+2, newVerts, newFace_vert_ind) #the last added vertices (*2, because arc_vert contains only one half) (+ the 2 before that, which are the 90° cut)
                            
        ################################################
                else:
        ###### case: 2 connecting edges, street pass through ######
                    if edgeConnections < 3: 
                        ########### calculate all necessary variables that would be needed if the the corners angle is lower than the threshold and high enough to create an arc ###########
                        edgeR = vm.link_edges[0] #get the connected edge
                        edgeL = vm.link_edges[1] #get the connected edge
                        #subtracting the corner vertex coordinates, we need the other vectors relative position to the corner vertex
                        vm_vR = edgeR.other_vert(vm).co - vm.co #get vertex1 connected to current processed vertex #rel coord to vm.co
                        vm_vL = edgeL.other_vert(vm).co - vm.co #get vertex2 connected to current processed vertex #rel coord to vm.co
                        
                        corner_normal = MakeNormalVector(vm_vR, vm_vL) #vecor that points up/down from the imaginary plane made from the two input vectors                
                        if corner_normal[2] < 0: #is the corner normal pointing downwards?
                            #reverse normal direction
                            corner_normal *= -1
                            #reverse edge data and edge vectors
                            temp = edgeR
                            edgeR = edgeL
                            edgeL = temp
                            
                            temp = vm_vR
                            vm_vR = vm_vL
                            vm_vL = temp
                        
                        corner_StrWidthR_direct = (corner_normal.cross(vm_vR)/ (numpy.linalg.norm(corner_normal.cross(vm_vR)))) #directional vector (length=1) from corner to the inside of the street width in a 90° angle
                        vm_vR_direct = vm_vR / numpy.linalg.norm(vm_vR) #directinal vector (length=1) of street 1
                        vm_vL_direct = vm_vL / numpy.linalg.norm(vm_vL) #directinal vector (length=1) of street 2
                        
                        #cos(angle)=dotProduct(v1,v2)/(|v1|*|v2|) = normalized (length of 1) vectors, that's why we divide by their multiplied length (|v1|*|v2|)
                        #numpy.clip because the result sometime gets out of bounds of -1 to 1
                        rad_street = math.acos(numpy.clip(numpy.dot(vm_vR_direct,vm_vL_direct),-1,1)) #radiens (angle) between the two streets
                        rad_alpha = rad_street / 2 #the angle of alpha in the right triangle
                        rad_arc = math.pi - rad_street #the angle the arc needs to cover/describe
                        
                        b = StrWidthHalf / math.tan(rad_alpha) #b = a / tan(alpha)
                        
                    ############ below max angle threshold ############
                        if rad_street <= rad_thr: #if true, create an arc
                            b += BevelSize #add bevel-edge-length to calcualte the arc_center
                            a = b * math.tan(rad_alpha)
                            arc_radius = a - StrWidthHalf
                            #if B.cross(-bev1_B)[2]>0: #to the right of Side C (corner to B)?
                            corner_StrWidthL_direct = (vm_vL.cross(corner_normal)/(numpy.linalg.norm(corner_normal.cross(vm_vL)))) #directional vector (length=1) from corner to the inside of the street width in a 90° angle

                            #corner_StrWidthL_direct this vector has the angle (relative to the world) that the arc will need as an rotation offset
                            rad_offset = WorldAngleFromVector(-corner_StrWidthL_direct)
                            
                            #### create inner arc ####
                            
                            vm_bev1 = (corner_StrWidthR_direct * StrWidthHalf) + (vm_vR_direct * b) #bevel vertex coordinate, also the connecting vertex to the street, vm (middle vertex) as the origin - the other bevel will come from the arc creation
                            vm_bev2 = (corner_StrWidthL_direct * StrWidthHalf) + (vm_vL_direct * b) #bevel vertex coordinate, also the connecting vertex to the street, vm (middle vertex) as the origin - the other bevel will come from the arc creation
                            
                            arc_vert = [] #street connecting vertex coordinate, also first arc vertex
                            CreateArc(arc_vert, arc_radius, subdiv, rad_arc, rad_offset, True, False) #creates the arc at world origin (local space) #first vertex will be just for coordinate refrence, to be subtracted from every other
                            
                            if len(arc_vert) > 0:
                                for i in range(1,len(arc_vert)):
                                    arc_vert[i] = arc_vert[i] - arc_vert[0] + vm_bev2 #subtract to bring it to world origin and add to set it to the bevel corner
                                arc_vert.pop(0) #remove reference vertex
                            #add bevel vertex to the arc vertex (they are part of the arc)
                            arc_vert.append(vm_bev1)
                            arc_vert.insert(0,vm_bev2)
                            bev1_ind = len(newVerts) + len(arc_vert) - 1
                            bev2_ind = len(newVerts)
                            
                            ##### adding the vertices to the vertex list #####
                            for newVertCoord in arc_vert:
                                newVerts.append(newVertCoord+vm.co) #add the original vertex coordinate (vm.co)
                            addToVertFace(vm.index, len(arc_vert), newVerts, newFace_vert_ind) #addToVertFace(TargetKnot_ind, AddedVert_count, ExistingVert_list, newFaces_ind_list)
                            addToEdgeFace(edgeR, bev1_ind, vm, True) #the Bool (True/False) determins if the input is the left or right edge (determined by the cross product -> corner_normal)
                            addToEdgeFace(edgeL, bev2_ind, vm, False)
                            
                            #### create outer arc ####
                            
                            vm_bev1 = (-corner_StrWidthR_direct * StrWidthHalf) + (vm_vR_direct * b) #bevel vertex coordinate, also the connecting vertex to the street, vm (middle vertex) as the origin - the other bevel will come from the arc creation
                            vm_bev2 = (-corner_StrWidthL_direct * StrWidthHalf) + (vm_vL_direct * b) #bevel vertex coordinate, also the connecting vertex to the street, vm (middle vertex) as the origin - the other bevel will come from the arc creation
                            
                            arc_vert = []
                            arc_out_radius = a + StrWidthHalf
                            CreateArc(arc_vert, arc_out_radius, subdiv, rad_arc, rad_offset, True, False)
                            
                            if len(arc_vert) > 0:
                                for i in range(1,len(arc_vert)):
                                    arc_vert[i] = arc_vert[i] - arc_vert[0] + vm_bev2 #subtract to bring it to world origin and add to set it to the bevel corner
                                arc_vert.pop(0) #remove reference vertex
                                arc_vert.reverse() #for face building it needs to be in reverse order
                            #add bevel vertex to the arc vertex (they are part of the arc)
                            arc_vert.insert(0,vm_bev1)
                            arc_vert.append(vm_bev2)
                            bev1_ind = len(newVerts) #the verts are not added yet, so the last index+1 will be the index of this vertex
                            bev2_ind = len(newVerts) + len(arc_vert) - 1
                            
                            for newVertCoord in arc_vert:
                                ##### adding the vertices to the vertex list #####
                                newVerts.append(newVertCoord+vm.co)
                            
                            addToVertFace(vm.index, len(arc_vert), newVerts, newFace_vert_ind) #addToVertFace(TargetKnot_ind, AddedVert_count, ExistingVert_list, newFaces_ind_list)
                            #bool values are reversed, because the order of the vertex was reversed for the outer arc
                            addToEdgeFace(edgeR, bev1_ind, vm, False) #the Bool (True/False) determins if the input is the left or right edge (determined by the cross product -> corner_normal)
                            addToEdgeFace(edgeL, bev2_ind, vm, True)
                            
                    ############ above max angle threshold ############
                        else: #create just the Corner vertex
                            C_B = corner_StrWidthR_direct * StrWidthHalf #A_C=CrossProduct()
                            A_C = vm_vR_direct*b
                            A_B = A_C + C_B
                            newVerts.append(A_B+vm.co)
                            newVerts.append(-A_B+vm.co)
                            bev1_ind = len(newVerts) - 2
                            bev2_ind = len(newVerts) - 1
                            #add two last vertices that were just added to each newFace_edge
                            addToEdgeFace(edgeR, bev1_ind, vm, True) #the Bool (True/False) determins if the input is the left or right edge (determined by the cross product -> corner_normal)
                            addToEdgeFace(edgeR, bev2_ind, vm, False)
                            addToEdgeFace(edgeL, bev1_ind, vm, False) #the Bool (True/False) determins if the input is the left or right edge (determined by the cross product -> corner_normal)
                            addToEdgeFace(edgeL, bev2_ind, vm, True)
                    
        ###### case: 3 or more connecting edges, street crossing/knot ######
                    else:
######### create dot_list #########
                        dot_list = [] #here the dot product of each possible edge pair will be stored
                        smallest_dot_ind = -1 #the index will be calcualted at wich the fist arc and the length of b (in the right triangle) will be defined
                        edge_left_list = [] #for later counting, maybe there is an angle bigger than 180°
                        edge_right_list = [] #for later counting, maybe there is an angle bigger than 180°
                            
                        for j in range(0, edgeConnections):
                            vm_vR_direct = vm.link_edges[j].other_vert(vm).co - vm.co #vector from vm to v1
                            vm_vR_direct /= numpy.linalg.norm(vm_vR_direct)
                            
                            for k in range(j+1, edgeConnections): #calculate the left over angles
                                vm_vL_direct = vm.link_edges[k].other_vert(vm).co - vm.co #vector from vm to v2
                                vm_vL_direct /= numpy.linalg.norm(vm_vL_direct)
                                corner_normal = MakeNormalVector(vm_vR_direct, vm_vL_direct)
                                if corner_normal[2] < 0: #determin wich of the vectors is the right sided, because the arc vertices order will be counter clockwise
                                    #DotList(edge_right, edge_left, vec_right, vec_left, dot, normal, IsGap)
                                    dot_list.append(DotList(vm.link_edges[k], vm.link_edges[j], vm_vL_direct, vm_vR_direct, numpy.dot(vm_vR_direct,vm_vL_direct), -corner_normal, False))
                                else:
                                    #DotList(edge_right, edge_left, vec_right, vec_left, dot, normal, IsGap)
                                    dot_list.append(DotList(vm.link_edges[j], vm.link_edges[k], vm_vR_direct, vm_vL_direct, numpy.dot(vm_vR_direct,vm_vL_direct), corner_normal, False))
                                
                                if dot_list[smallest_dot_ind].dot <= dot_list[-1].dot: #bigger dot prduct (-1,1) means a smaller resulting angle, want to start with the smallest angle
                                    smallest_dot_ind = len(dot_list)-1 #entering the index for the dot_list with the smallest angle
                                    
######### sort dot_list by neighbour #########
                        #find out if there is an angle bigger than 180° between 2 edges, if there is one, it can only be one
                        #edges in the dot_list being the left/right one was determind based on the cross product vector pointing up/down. the order of the operants in the cross product dictates the direction of the resulting vector
                        #if an edge appears to be to the left/right to every other edge, it is part of two edges having a gaping angle bigger than 180°
                        gap_edge_left = None
                        gap_edge_right = None
                        gap_dot = None
                        sortedDot_list = [dot_list[smallest_dot_ind]] #addin the item with the smalles dot as the first item
                        for i in range(0, edgeConnections-1):
                            found_items = []
                            biggest_dot_item = DotList(None, None, None, None, -2, None, False)
                            smallest_dot_item = DotList(None, None, None, None, 2, None, False)
                            
                            for dot_item in dot_list:
                                if sortedDot_list[-1].edge_right == dot_item.edge_left: #is the right_edge on the left
                                    if biggest_dot_item.dot <= dot_item.dot:
                                        biggest_dot_item = dot_item
                                if sortedDot_list[-1].edge_right == dot_item.edge_right:
                                    found_items.append(dot_item)
                                    if smallest_dot_item.dot >= dot_item.dot: #in case there is a gap bigger than 180°, save the smallest dot (biggest angle)
                                        smallest_dot_item = dot_item
                                        
                            ### add item to sortedDot_list ###
                            if len(found_items) == edgeConnections-1: #if there is a gap bigger than 180° it should appear as the right edge relative to every other edge
                                #case: angle > 180° - a gap
                                smallest_dot_item.IsGap = True #mark the entry as a gap bigger than 180°                        
                                #change out the edge references
                                temp = smallest_dot_item.edge_right
                                smallest_dot_item.edge_right = smallest_dot_item.edge_left
                                smallest_dot_item.edge_left = temp
                                #change out the direction vectors of the edges
                                temp = smallest_dot_item.vec_right
                                smallest_dot_item.vec_right = smallest_dot_item.vec_left
                                smallest_dot_item.vec_left = temp
                                
                                sortedDot_list.append(smallest_dot_item) #add the now conform item
                            else:
                                #case: angle < 180° (more likely)
                                sortedDot_list.append(biggest_dot_item)
                        
######### create arcs #########
                        
                        ##### calculate the side length b for the whole street knot fro the smalles angle ####
                        #numpy.clip because the result sometime gets out of bounds (-1...1) of the acos function
                        rad_street = math.acos(numpy.clip(sortedDot_list[0].dot,-1,1)) #radiens (angle) between the two streets
                        rad_alpha = rad_street/2 #the angle of alpha in the right triangle
                        rad_arc = math.pi-rad_street #the angle the arc needs to cover/describe
                                    
                        b_knot = StrWidthHalf / math.tan(rad_alpha) #b = a / tan(alpha) #side length b of the of the right triangle, to calculate the arc center
                        b = b_knot + BevelSize #add bevel-edge-length to calcualte the arc_center
                            
                        for dot_item in sortedDot_list:
                            ########### set all necessary variables that would be needed if the the corners angle is lower than the threshold and high enough to create an arc ###########
                            edgeR = dot_item.edge_right #get the connected edge
                            edgeL = dot_item.edge_left #get the connected edge
                            #subtracting the corner vertex coordinates, we need the other vectors relative position to the corner vertex
                            vm_vR = dot_item.vec_right #get vertex1 connected to current processed vertex #rel coord to vm.co
                            vm_vL = dot_item.vec_left #get vertex2 connected to current processed vertex #rel coord to vm.co
                            
                            corner_normal = dot_item.normal #vecor that points up/down from the imaginary plane made from the two input vectors
                            
                            corner_StrWidthR_direct = (corner_normal.cross(vm_vR) / (numpy.linalg.norm(corner_normal.cross(vm_vR)))) #directional vector (length=1) from corner to the inside of the street width in a 90° angle
                            corner_StrWidthL_direct = (vm_vL.cross(corner_normal) / (numpy.linalg.norm(corner_normal.cross(vm_vL)))) #directional vector (length=1) from corner to the inside of the street width in a 90° angle
                            
                            vm_vR_direct = dot_item.vec_right #directinal vector (length=1) of street right
                            vm_vL_direct = dot_item.vec_left #directinal vector (length=1) of street left
                            
                            #numpy.clip because the result sometime gets out of bounds of -1 to 1
                            rad_street = math.acos(numpy.clip(dot_item.dot, -1, 1)) #radiens (angle) between the two streets
                            rad_alpha = rad_street / 2 #the angle of alpha in the right triangle
                            rad_arc = math.pi - rad_street #the angle the arc needs to cover/describe
                            
                            #### Create verts for Gap ####
                            if dot_item.IsGap == False:
                                #case: regular angle, smaller than 180°
                            ############ below max angle threshold ############
                                if rad_street <= rad_thr:
                                    a = b * math.tan(rad_alpha)
                                    arc_radius = a - StrWidthHalf
                                    
                                    #corner_StrWidthL_direct this vector has the angle (relative to the world) that the arc will need as an rotation offset
                                    rad_offset = WorldAngleFromVector(-corner_StrWidthL_direct) #gamma=acos(x/r) || angle the arc needs to be rotated, positive x direction would be the first vertex (polar coordinates)
                                    
                                    vm_bev1 = (corner_StrWidthR_direct * StrWidthHalf) + (vm_vR_direct * b) #bevel vertex coordinate, also the connecting vertex to the street, vm (middle vertex) as the origin - the other bevel will come from the arc creation
                                    vm_bev2 = (corner_StrWidthL_direct * StrWidthHalf) + (vm_vL_direct * b) #bevel vertex coordinate, also the connecting vertex to the street, vm (middle vertex) as the origin - the other bevel will come from the arc creation
                                    
                                    arc_vert = [] #street connecting vertex coordinate, also first arc vertex
                                    CreateArc(arc_vert, arc_radius, subdiv, rad_arc, rad_offset, True, False) #creates the arc at world origin (local space)
                                    
                                    if len(arc_vert) > 0:
                                        for i in range(1,len(arc_vert)):
                                            arc_vert[i] = arc_vert[i] - arc_vert[0] + vm_bev2 #subtract to bring it to world origin and add to set it to the bevel corner
                                        arc_vert.pop(0) #remove reference vertex
                                    #add bevel vertex to the arc vertex (they are part of the arc)
                                    arc_vert.append(vm_bev1)
                                    arc_vert.insert(0,vm_bev2)
                                    bev1_ind = len(newVerts) + len(arc_vert) - 1
                                    bev2_ind = len(newVerts)
                                    
                                    for newVertCoord in arc_vert:
                                        ##### adding the vertices to the vertex list #####
                                        newVerts.append(newVertCoord+vm.co)
                                    
                                    addToVertFace(vm.index, len(arc_vert), newVerts, newFace_vert_ind) #addToVertFace(TargetKnot_ind, AddedVert_count, ExistingVert_list, newFaces_ind_list)
                                    addToEdgeFace(edgeR, bev1_ind, vm, True) #the Bool (True/False) determins if the input is the left or right edge (determined by the cross product -> corner_normal)
                                    addToEdgeFace(edgeL, bev2_ind, vm, False)
                                
                                #### above max angle threshold ####
                                else: #create just the Corner vertex
                                    
                                    bevR = (corner_StrWidthR_direct * StrWidthHalf) + (vm_vR_direct * b) #bevel vertex from the right edge
                                    bevL = (corner_StrWidthL_direct * StrWidthHalf) + (vm_vL_direct * b) #
                                    
                                    #recalculate b length for the inner edge, b_knot and b were calculated for the smalles angle in the street_knot, this doesn't apply for the single vertex
                                    b_extra = StrWidthHalf / math.tan(math.acos(numpy.clip(dot_item.dot,-1,1)) / 2) #b = a / tan(alpha)
                                    A_B = (corner_StrWidthR_direct * StrWidthHalf) + (vm_vR_direct*b_extra)
                                    
                                    newVerts.append(bevL+vm.co)
                                    newVerts.append(A_B+vm.co)                            
                                    newVerts.append(bevR+vm.co)
                                    
                                    bevL_ind = len(newVerts) - 3
                                    corner_in = len(newVerts) - 2
                                    bevR_ind = len(newVerts) - 1
                                    addToVertFace(vm.index, 3, newVerts, newFace_vert_ind) #addToVertFace(TargetKnot_ind, AddedVert_count, ExistingVert_list, newFaces_ind_list)
                                    #add two last vertices that were just added to each newFace_edge
                                    addToEdgeFace(edgeR, bevR_ind, vm, True) #the Bool determins if the input belongs to the right edge (True) or the left edgte (False)(determined by the cross product -> corner_normal)
                                    addToEdgeFace(edgeL, bevL_ind, vm, False) #the Bool determins if the input belongs to the right edge (True) or the left edgte (False)(determined by the cross product -> corner_normal)
                            
                            else:
                                ############ create outer arc ############
                                # case: angle bigger than 180°
                                if rad_street <= rad_thr:
                                    arc_vert = []
                                    
                                    rad_alpha = math.acos(numpy.clip(dot_item.dot, -1, 1)) / 2 #radiens (angle) between the two streets
                                    a = b * math.tan(rad_alpha)
                                    arc_out_radius = a + StrWidthHalf #for the outer arc radius it needs too add half the streetwidth, inner radius would need to subtract
                                    rad_offset = math.acos(numpy.clip(corner_StrWidthR_direct[0],-1, 1))
                                    if corner_StrWidthR_direct[1] < 0: #is the vector pointing below the x axis (lookin at the y-value)
                                        rad_offset = (2*math.pi)-rad_offset #360-(calulated angle)
                                    
                                    bevR = (corner_StrWidthR_direct * StrWidthHalf) + (vm_vR_direct * b) #bevel vertex from the right edge
                                    bevL = (corner_StrWidthL_direct * StrWidthHalf) + (vm_vL_direct * b) #bevel vertex from the left edge
                                    
                                    CreateArc(arc_vert, arc_out_radius, subdiv, rad_arc, rad_offset, True, False)
                                    
                                    if len(arc_vert) > 0:
                                        for i in range(1,len(arc_vert)):
                                            arc_vert[i] = arc_vert[i] - arc_vert[0] + bevR #subtract to bring it to world origin and add to set it to the bevel corner
                                        arc_vert.pop(0) #remove reference vertex
                                        arc_vert.reverse() #for face building it needs to be in reverse order
                                    #add bevel vertex to the arc vertex (they are part of the arc)
                                    arc_vert.insert(0,bevL)
                                    arc_vert.append(bevR)
                                    bevL_ind = len(newVerts) #the verts are not added yet, so the last index+1 will be the index of this vertex
                                    bevR_ind = len(newVerts) + len(arc_vert) - 1
                                    
                                    for newVertCoord in arc_vert:                                
                                        newVerts.append(newVertCoord+vm.co)##### adding the vertices to the vertex list #####
                                    
                                    addToVertFace(vm.index, len(arc_vert), newVerts, newFace_vert_ind) #addToVertFace(TargetKnot_ind, AddedVert_count, ExistingVert_list, newFaces_ind_list)
                                    #bool values are reversed, because the order of the vertex was reversed for the outer arc
                                    addToEdgeFace(edgeR, bevR_ind, vm, True) #addToEdgeFace(edge, bev_ind, vm, isRightEdge)
                                    addToEdgeFace(edgeL, bevL_ind, vm, False)
                                
                                #### above max angle threshold ####
                                else:
                                    bevR = (corner_StrWidthR_direct * StrWidthHalf) + (vm_vR_direct * b) #bevel vertex from the right edge
                                    bevL = (corner_StrWidthL_direct * StrWidthHalf) + (vm_vL_direct * b) #
                                    
                                    #recalculate b length for the inner edge, b_knot and b were calculated for the smalles angle in the street_knot, this doesn't apply for the single vertex
                                    b_extra = StrWidthHalf / math.tan(math.acos(numpy.clip(dot_item.dot,-1,1)) / 2) #b = a / tan(alpha)
                                    A_B = (corner_StrWidthR_direct * StrWidthHalf) - (vm_vR_direct*b_extra)
                                    
                                    newVerts.append(bevL+vm.co)
                                    newVerts.append(A_B+vm.co)                            
                                    newVerts.append(bevR+vm.co)
                                    
                                    bevL_ind = len(newVerts) - 3
                                    corner_in = len(newVerts) - 2
                                    bevR_ind = len(newVerts) - 1
                                    addToVertFace(vm.index, 3, newVerts, newFace_vert_ind) #addToVertFace(TargetKnot_ind, AddedVert_count, ExistingVert_list, newFaces_ind_list)
                                    #add two last vertices that were just added to each newFace_edge
                                    addToEdgeFace(edgeR, bevR_ind, vm, True) #the Bool determins if the input belongs to the right edge (True) or the left edgte (False)(determined by the cross product -> corner_normal)
                                    addToEdgeFace(edgeL, bevL_ind, vm, False) #the Bool determins if the input belongs to the right edge (True) or the left edgte (False)(determined by the cross product -> corner_normal)

            v_remain.pop(0) #the street for this vertex is done, so delete first element from the list


        bm.to_mesh(me)
        bm.free()  # free and prevent further access

        ############ remove empty (unused) face 'slots' from the list ############
        i=0
        while i != (len(newFace_vert_ind)):
            if newFace_vert_ind[i] == []:
                newFace_vert_ind.pop(i)
            else:
                i += 1
        ########################################################################
        i=0
        while i != (len(newFaces_edge_ind)):
            if newFaces_edge_ind[i][0] == [] or newFaces_edge_ind[i][1] == [] or newFaces_edge_ind[i][2] == [] or newFaces_edge_ind[i][3] == []:
                newFaces_edge_ind.pop(i)
            else:
                i += 1
        ########################################################################
        #debug
        #print(newFaces_edge_ind)

        newFace_vert_ind.extend(newFaces_edge_ind)
        createMesh(newVerts,newFace_vert_ind)
        
        return {'FINISHED'} #CANCELED
    
def register():
    bpy.utils.register_class(OBJECT_OT_Street_from_edges)
    bpy.utils.register_class(VIEW3D_PT_Street_from_edges)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_Street_from_edges)
    bpy.utils.unregister_class(VIEW3D_PT_Street_from_edges)

if __name__ == '__main__':
    register()